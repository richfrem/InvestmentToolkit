import subprocess
import json
import pytest

def test_cash_account_regex_matching():
    # Test text simulating the dropdown button text for Cash account
    test_text = "Cash - 40049489"
    
    # We want to run a quick node snippet that evaluates the regex we use in trading.js
    # and check if it parses "Cash" correctly.
    # The regex in trading.js before fix:
    #   const regex_before = /(TFSA|RRSP|Margin|Individual)[\s\-]+(\d{4,})/i;
    # The regex after fix:
    #   const regex_after = /(TFSA|RRSP|Margin|Individual|Cash)[\s\-]+(\d{4,})/i;
    
    js_code = f"""
    const text = {json.dumps(test_text)};
    // BEFORE fix regex:
    const regexBefore = /(TFSA|RRSP|Margin|Individual)[\\s\\-]+(\\d{{4,}})/i;
    const matchBefore = text.match(regexBefore);
    
    // AFTER fix regex (what we want to implement):
    const regexAfter = /(TFSA|RRSP|Margin|Individual|Cash)[\\s\\-]+(\\d{{4,}})/i;
    const matchAfter = text.match(regexAfter);
    
    console.log(JSON.stringify({{
        before: matchBefore ? matchBefore[1].toUpperCase() : null,
        after: matchAfter ? matchAfter[1].toUpperCase() : null
    }}));
    """
    
    r = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True, text=True, check=True
    )
    result = json.loads(r.stdout.strip())
    
    # Under the old regex, it should fail to match (result is null)
    # Under the new regex, it should match "CASH"
    assert result["before"] is None, "Before regex should not match Cash"
    assert result["after"] == "CASH", "After regex should match Cash"

def test_trading_js_evaluation_on_cash():
    # This test verifies if trading.js actually uses the updated regex.
    # We will read trading.js, extract the active account match regex, and check if it matches "Cash".
    from pathlib import Path
    trading_js_path = Path(__file__).resolve().parents[3] / "tradingview-cdp" / "core" / "trading.js"
    content = trading_js_path.read_text()
    
    # Let's check if the regex matches 'Cash'. If the regex is not yet updated, this test will fail!
    # This is the RED phase of TDD.
    import re
    matches = re.findall(r'accountText\.match\((.*?)\)', content)
    assert len(matches) > 0, "Could not find accountText.match in trading.js"
    
    # Check if the regex pattern contains 'Cash'
    pattern_str = matches[0]
    assert 'Cash' in pattern_str or 'CASH' in pattern_str, f"Regex pattern {pattern_str} in trading.js does not contain 'Cash'"

def test_open_order_dialog_bypasses_if_already_open():
    # Verify that openOrderDialog checks if getOrderDialogState() is already open
    # before trying to click the overlay button.
    from pathlib import Path
    trading_js_path = Path(__file__).resolve().parents[3] / "tradingview-cdp" / "core" / "trading.js"
    content = trading_js_path.read_text()
    
    # We expect openOrderDialog to call getOrderDialogState or check dialog state
    # This is the RED phase: the check does not exist yet.
    assert "getOrderDialogState" in content, "getOrderDialogState should be defined"
    
    # Let's check if the openOrderDialog function contains a check for state.open or getOrderDialogState
    # Locate openOrderDialog definition
    func_idx = content.find("async function openOrderDialog")
    assert func_idx != -1, "Could not find openOrderDialog function"
    
    func_body = content[func_idx:func_idx + 800]
    assert "getOrderDialogState" in func_body, "openOrderDialog should check if the dialog is already open using getOrderDialogState"

def test_buy_sell_button_text_matching():
    # Verify that the text-matching in openOrderDialog checks for .includes() rather than exact match
    # to support labels like "100.01 BUY".
    from pathlib import Path
    trading_js_path = Path(__file__).resolve().parents[3] / "tradingview-cdp" / "core" / "trading.js"
    content = trading_js_path.read_text()
    
    # We want to make sure it matches text by checking .indexOf() or .includes() case-insensitively
    assert "el.textContent.toUpperCase().includes" in content or "el.textContent.trim().toUpperCase().indexOf" in content, \
        "openOrderDialog button text matching should use case-insensitive includes check"

def test_switch_chart_symbol_bypasses_if_already_active():
    # Verify that switchChartSymbol checks if the target symbol matches document.title
    # and returns early if it is already active.
    from pathlib import Path
    trading_js_path = Path(__file__).resolve().parents[3] / "tradingview-cdp" / "core" / "trading.js"
    content = trading_js_path.read_text()
    
    # Locate switchChartSymbol definition
    func_idx = content.find("async function switchChartSymbol")
    assert func_idx != -1, "Could not find switchChartSymbol function"
    
    func_body = content[func_idx:func_idx + 800]
    assert "document.title" in func_body, "switchChartSymbol should check document.title to see if symbol is already active"

def test_switch_chart_symbol_keycode_mapping():
    # Verify that keycodes for Period (.) and Minus (-) are correctly mapped
    # in switchChartSymbol in trading.js.
    from pathlib import Path
    trading_js_path = Path(__file__).resolve().parents[3] / "tradingview-cdp" / "core" / "trading.js"
    content = trading_js_path.read_text()
    
    # We check if there is an explicit mapping of vkey/keyCode for '.' and '-' to 190 and 189
    assert "190" in content, "Should have virtual keycode 190 for Period"
    assert "189" in content, "Should have virtual keycode 189 for Minus"

def test_select_account_robust_matching():
    # Verify that selectAccount in trading.js searches for spans with empty className matches
    # to select account dropdown items.
    from pathlib import Path
    trading_js_path = Path(__file__).resolve().parents[3] / "tradingview-cdp" / "core" / "trading.js"
    content = trading_js_path.read_text()
    
    # Locate selectAccount definition
    func_idx = content.find("async function selectAccount")
    assert func_idx != -1, "Could not find selectAccount function"
    
    func_body = content[func_idx:func_idx + 1200]
    assert "s.className === ''" in func_body or 's.className === ""' in func_body, \
        "selectAccount should check for empty className on spans"
    assert "MouseEvent" in func_body, \
        "selectAccount should dispatch mousedown/mouseup MouseEvents to reliably open the dropdown"

def test_execute_order_closes_stale_dialog():
    # Verify that executeOrder in trading.js closes any existing order dialog first
    # to prevent account-leak bugs.
    from pathlib import Path
    trading_js_path = Path(__file__).resolve().parents[3] / "tradingview-cdp" / "core" / "trading.js"
    content = trading_js_path.read_text()
    
    # Locate executeOrder definition
    func_idx = content.find("export async function executeOrder")
    assert func_idx != -1, "Could not find executeOrder function"
    
    func_body = content[func_idx:func_idx + 800]
    assert "closeOrderDialog" in func_body, "executeOrder should call closeOrderDialog at the beginning to clean state"






