# 📈 Pine Script™ v6 Reference & Learning Package for AI Agents

**Version:** Pine Script™ v6
**Target Audience:** AI Developer Agents / Code Generators
**Purpose:** Comprehensive reference material for generating, debugging, and optimizing Pine Script v6 code.
Referemce: https://www.tradingview.com/pine-script-reference/v6/
---

## 1. 🚀 What's New in Pine Script v6 (Critical for AI Agents)
*If you are migrating logic from v5, you MUST apply these rules.*

- **Dynamic Data Requests:** `request.*()` functions now natively accept `series string` arguments. You can request data dynamically in loops, `if` statements, and library exports. No need for `dynamic_requests=true` anymore.
- **Short-Circuit Logical Evaluation:** The `and` and `or` operators now evaluate lazily. E.g., `if array.size(arr) > 0 and array.get(arr, 0) == 1` will no longer crash if the array is empty.
- **Strict Booleans:** Booleans are strictly `true` or `false`. `na` no longer implicitly casts to `bool`. Functions like `na()` and `nz()` do not accept `bool`.
- **Typographic Text Sizing & Formatting:** `size` and `text_size` properties in labels, boxes, and tables accept `int` (typographic points) instead of just `size.*` constants. `text_formatting` added (`text.format_bold`, `text.format_italic`, `text.format_none`).
- **Strategy Order Trimming:** Strategies no longer crash at the 9000-trade limit. Older trades are automatically trimmed. Track with `strategy.closedtrades.first_index`.
- **Negative Array Indices:** `array.get(myArray, -1)` accesses the last element.
- **Division:** Division of two `const int` values can return a fractional value.

---

## 2. 🏗️ Script Structure & Declarations
Every script must start with `//@version=6` and a declaration statement.

### 2.1 Indicators

```

```text
File generated successfully.

```pine
//@version=6
indicator("My Indicator", shorttitle="MI", overlay=true, timeframe="", timeframe_gaps=true)

```

### 2.2 Strategies

```pine
//@version=6
strategy("My Strategy", overlay=true, margin_long=100, margin_short=100, calc_on_every_tick=false)

```

### 2.3 Libraries

```pine
//@version=6
library("MyLibrary")

```

---

## 3. 🧬 Type System & Qualifiers

Pine Script types consist of a **Type** and a **Qualifier**.

**Types:** `int`, `float`, `bool`, `color`, `string`, `line`, `label`, `box`, `table`, `array`, `matrix`, `map`, User-Defined Types (UDTs).
**Qualifiers** (determine when a value is known):

1. **const:** Known at compile-time (e.g., `10`, `"Hello"`).
2. **input:** Known at configuration time (via `input.*()`).
3. **simple:** Known at bar 0 (first script execution).
4. **series:** Can change on every bar. Default for runtime calculations (e.g., `close`, `high`, dynamic variables).

---

## 4. 🧮 Variables & Operators

### 4.1 Variable Assignment

* `=` : Initialization.
* `:=` : Reassignment (must use `:=` to update mutable variables).

### 4.2 Variable Modifiers

* `var` : Initializes the variable *only once* on the first bar. State is preserved across bars.
* `varip` : Initializes only once. State is preserved across *real-time ticks* inside a single bar.

```pine
var int count = 0
if close > open
    count := count + 1 // Updates persistent counter

```

### 4.3 Operators

* **Math:** `+`, `-`, `*`, `/`, `%`
* **Comparison:** `==`, `!=`, `<`, `<=`, `>`, `>=`
* **Logical:** `not`, `and`, `or` (Now short-circuited in v6)
* **Ternary:** `condition ? true_val : false_val`
* **History Referencing:** `[]` e.g., `close[1]` (previous bar's close). In v6, cannot directly reference literal history or UDT fields.

---

## 5. 🔀 Control Structures

### 5.1 If Statement

```pine
var result = 0.0
if close > open
    result := close
else if close < open
    result := open
else
    result := hl2

```

### 5.2 Switch Statement

```pine
color c = switch
    close > open => color.green
    close < open => color.red
    => color.gray

```

### 5.3 Loops (`for`, `for...in`, `while`)

```pine
// For loop
float sum = 0.0
for i = 0 to 9
    sum := sum + close[i]

// For...in (Iterating Collections)
a = array.from(1, 2, 3)
for element in a
    sum := sum + element

// While loop
int i = 0
while i < 10
    sum := sum + i
    i += 1

```

---

## 6. 📦 Collections (Arrays, Matrices, Maps)

### 6.1 Arrays

1D collections of elements. In v6, negative indices are supported!

```pine
arr = array.new_float(0)
array.push(arr, close)
last_val = array.get(arr, -1) // v6 feature
array.insert(arr, 0, open)
array.remove(arr, 0)

```

### 6.2 Matrices

2D grids of elements.

```pine
mat = matrix.new<float>(2, 2, 0.0) // 2 rows, 2 columns
matrix.set(mat, 0, 0, close)

```

### 6.3 Maps

Key-value pairs.

```pine
myMap = map.new<string, float>()
map.put(myMap, "AAPL", 150.0)
float val = map.get(myMap, "AAPL")

```

---

## 7. 🧩 User-Defined Types (UDTs) & Objects

Create custom object structures.

```pine
type PivotPoint
    int bar_time
    float price
    bool is_high

// Instantiation
myPivot = PivotPoint.new(time, high, true)
// Access/Update
myPivot.price := close

```

### 7.1 Methods

Functions attached to types.

```pine
method getRange(PivotPoint this) =>
    this.price - low

range = myPivot.getRange()

```

---

## 8. 🌐 Dynamic Data Requests (`request.*`) [v6 Highlight]

In v6, `request.*` handles dynamic `series string` for symbols and timeframes.

```pine
//@version=6
indicator("Dynamic Requests")
symbols = array.from("AAPL", "MSFT", "GOOG")

// Valid in v6: requesting inside a loop dynamically
for sym in symbols
    c = request.security(sym, "1D", close)
    // process c...

```

---

## 9. 🛠️ Built-in Namespaces & Key Functions

### 9.1 Technical Analysis (`ta.*`)

* `ta.sma(source, length)`, `ta.ema()`, `ta.rma()`, `ta.wma()`, `ta.vwma()`
* `ta.macd(source, fastlen, slowlen, siglen)`
* `ta.rsi(source, length)`
* `ta.highest(source, length)`, `ta.lowest()`
* `ta.crossover(source1, source2)`, `ta.crossunder()`
* `ta.barssince(condition)`

### 9.2 Math (`math.*`)

* `math.abs()`, `math.log()`, `math.max()`, `math.min()`, `math.round()`

### 9.3 String (`str.*`)

* `str.tostring(value, format)`, `str.format("Price: {0}", close)`
* `str.length()`, `str.split()`

### 9.4 Math/Stat (`math.*`)

* `math.random(min, max)`

### 9.5 Drawing & Visuals (`plot`, `line`, `box`, `label`, `table`)

* **Plot:** `plot(close, color=color.red, linewidth=2)`
* **Label (v6 Text Formatting):** ```pine
label.new(bar_index, high, "Text", text_size=14, text_formatting=text.format_bold)
```

```


* **Line:** `line.new(x1, y1, x2, y2, xloc=xloc.bar_index)`
* **Box:** `box.new(left, top, right, bottom)`
* **Table:** ```pine
var tbl = table.new(position.top_right, 2, 2)
if barstate.islast
table.cell(tbl, 0, 0, "Price", text_color=color.white)
```


```



---

## 10. 🏦 Strategy Management (`strategy.*`)

Functions to automate trading limits, margins, and order execution.

* **Entry/Exit:** `strategy.entry(id, direction, qty, limit, stop)`
* **Exit:** `strategy.exit(id, from_entry, qty, profit, loss, trail_points)`
* **Close:** `strategy.close(id, comment)`
* **Data Variables:** - `strategy.position_size`
* `strategy.position_avg_price`
* `strategy.netprofit`
* `strategy.closedtrades.first_index` (v6: handles trimmed trades gracefully).


* **Directions:** `strategy.long`, `strategy.short`

---

## 11. 💡 Best Practices for AI Code Generation

1. **Always use `//@version=6`.**
2. **Declare `var` carefully.** Only use `var` for initialization that must persist across historical bars without resetting.
3. **Use `:=` for assignment.** A common error is using `=` when trying to mutate an existing variable.
4. **Avoid loops when vector operations exist.** E.g., `ta.sma` is faster than a `for` loop.
5. **Leverage Short-Circuiting.** Always place safety checks first: `if array.size(arr) > 0 and array.get(arr,0) == 1`.
6. **Type strictness.** Never pass a `bool` to `na()` or `nz()`.
7. **Drawings:** Only draw on `barstate.islast` when applicable, or delete old drawings using `line.delete()` to avoid chart clutter and memory leaks.

---

*Generated as a direct artifact for LLM and Developer usage based on official TradingView Pine Script™ v6 Reference Manuals.*
