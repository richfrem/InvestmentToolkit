import { getClient, evaluate } from './connection.js';

async function main() {
  try {
    const c = await getClient();
    console.log("CDP Connected.");
    
    // First let's click the dropdown button to open the menu, so the spans are loaded in DOM
    console.log("Opening dropdown...");
    const opened = await evaluate(`(function() {
      var btn = [...document.querySelectorAll('[class*="dropdownButton"]')].find(function(b) {
        return /TFSA|RRSP|Margin|Individual|Cash/i.test(b.textContent);
      }) || document.querySelector('[class*="dropdownButton"]');
      if (!btn) return 'Dropdown button not found';
      ['mousedown', 'mouseup', 'click'].forEach(function(t) {
        btn.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true }));
      });
      return 'Opened dropdown button text: ' + btn.textContent.trim();
    })()`);
    console.log("Status:", opened);

    // Sleep 1 second for render
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Find and list all spans
    console.log("Inspecting spans in DOM...");
    const spans = await evaluate(`(function() {
      var allSpans = [...document.querySelectorAll('span')];
      var pattern = /^(TFSA|RRSP|Cash|Margin|Individual)[\\s\\S]*\\d{4,}/i;
      return allSpans.map(function(s, idx) {
        var txt = s.textContent.trim();
        var isMatch = pattern.test(txt);
        var containsAny = /TFSA|RRSP|Cash|Margin/i.test(txt);
        if (containsAny) {
          return {
            index: idx,
            text: txt,
            className: s.className,
            patternMatch: isMatch,
            parentTagName: s.parentElement ? s.parentElement.tagName : null,
            parentClass: s.parentElement ? s.parentElement.className : null
          };
        }
        return null;
      }).filter(Boolean);
    })()`);

    console.log("Found matching spans:", JSON.stringify(spans, null, 2));

    // Close dropdown
    await evaluate(`(function() {
      var btn = [...document.querySelectorAll('[class*="dropdownButton"]')].find(function(b) {
        return /TFSA|RRSP|Margin|Individual|Cash/i.test(b.textContent);
      }) || document.querySelector('[class*="dropdownButton"]');
      if (btn) {
        ['mousedown', 'mouseup', 'click'].forEach(function(t) {
          btn.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true }));
        });
      }
    })()`);

    process.exit(0);
  } catch (e) {
    console.error("Error:", e);
    process.exit(1);
  }
}

main();
