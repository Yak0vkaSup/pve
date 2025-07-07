<template>
  <div class="docs-container">
    <!-- Sidebar Navigation -->
    <div class="docs-sidebar">
      <div class="sidebar-header">
        <h3>VPL Node Documentation</h3>
      </div>
      
      <div class="sidebar-content">
        <div class="node-category" v-for="category in nodeCategories" :key="category.name">
          <h4 class="category-title" @click="toggleCategory(category.name)">
            <i :class="category.expanded ? 'fas fa-chevron-down' : 'fas fa-chevron-right'"></i>
            {{ category.displayName }}
          </h4>
          <ul class="node-list" v-show="category.expanded">
            <li v-for="node in category.nodes" :key="node.type" 
                :class="{ active: activeNode === node.type }"
                @click="scrollToNode(node.type)">
              {{ node.name }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="docs-content">
      <div class="content-header">
        <h1>VPL Node Reference</h1>
        <p>Comprehensive documentation for all Visual Programming Language nodes in the system.</p>
        
        <div class="overview-section">
          <h2>Overview</h2>
          <p>The Visual Programming Language (VPL) system provides a comprehensive set of nodes for creating sophisticated trading strategies. Each node represents a specific function or operation that can be connected to other nodes to build complex trading logic.</p>
          
          <div class="quick-start">
            <h3>Quick Start Guide</h3>
            <ul>
              <li><strong>Data Access Nodes:</strong> Extract OHLCV data from market feeds</li>
              <li><strong>Set Value Nodes:</strong> Provide constant values (numbers, strings, booleans)</li>
              <li><strong>Math Operations:</strong> Perform arithmetic calculations</li>
              <li><strong>Technical Indicators:</strong> Calculate moving averages and other indicators</li>
              <li><strong>Comparison Nodes:</strong> Compare values and detect crossovers</li>
              <li><strong>Logic Operations:</strong> Combine conditions with AND, OR, NOT logic</li>
              <li><strong>Trading Operations:</strong> Create, modify, and cancel orders</li>
              <li><strong>Chart Tools:</strong> Add visual indicators and signals to charts</li>
              <li><strong>Communication:</strong> Send notifications via Telegram</li>
              <li><strong>Utilities:</strong> Helper functions for data validation</li>
            </ul>
          </div>
          
          <div class="data-types">
            <h3>Data Types</h3>
            <p>The VPL system uses typed connections between nodes. Each data type has a specific color for easy visual identification:</p>
            <ul>
              <li><span class="data-type-color" style="background-color: #d2ffb0;"></span><strong>Integer:</strong> Whole numbers (periods, counts, quantities)</li>
              <li><span class="data-type-color" style="background-color: #b0e0ff;"></span><strong>Float:</strong> Decimal numbers (prices, percentages, indicators)</li>
              <li><span class="data-type-color" style="background-color: #f3b0ff;"></span><strong>String:</strong> Text values (messages, symbols, order IDs)</li>
              <li><span class="data-type-color" style="background-color: #F77;"></span><strong>Bool:</strong> True/false conditions (signals, comparisons)</li>
              <li><span class="data-type-color" style="background-color: #fffdb0;"></span><strong>Object:</strong> Complex data structures (arrays, market data)</li>
              <li><span class="data-type-color" style="background-color: #dff4fb;"></span><strong>Exec:</strong> Execution signals ("GO" triggers for actions)</li>
            </ul>
          </div>

          <div class="execution-model">
            <h3>Execution Model</h3>
            <p>Understanding how nodes execute is crucial for building effective strategies:</p>
            <ul>
              <li><strong>Per-Candle Execution:</strong> All nodes execute once for each candle/bar in your timeframe</li>
              <li><strong>Sequential Processing:</strong> Nodes execute in topological order based on their connections</li>
              <li><strong>State Preservation:</strong> Stateful nodes (like indicators) maintain their internal state between candles</li>
              <li><strong>Real-time Updates:</strong> In live mode, nodes process new candles as they form</li>
              <li><strong>Order Management:</strong> Trading nodes track orders across multiple candle executions</li>
            </ul>
          </div>

          <div class="modes-info">
            <h3>Execution Modes</h3>
            <p>The system supports two execution modes:</p>
            <ul>
              <li><strong>Backtest Mode:</strong> Simulates trading on historical data for strategy validation</li>
              <li><strong>Live Mode:</strong> Executes real trades on Bybit exchange (requires API credentials)</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Data Access Nodes -->
      <section class="node-section" id="data-access">
        <h2>Data Access Nodes</h2>
        
        <!-- Get Open -->
        <div class="node-doc" id="get/open">
          <h3>Get Open <span class="node-type">get/open</span></h3>
          <p>Extracts the opening price from the current candle/bar data.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node reads directly from the current market data row.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>open</strong> (Float) - The opening price of the current candle</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>This node is typically used as a starting point to access historical or current opening prices for technical analysis, strategy logic, or order placement calculations.</p>
            </div>
          </div>
        </div>

        <!-- Get Close -->
        <div class="node-doc" id="get/close">
          <h3>Get Close <span class="node-type">get/close</span></h3>
          <p>Extracts the closing price from the current candle/bar data.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node reads directly from the current market data row.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>close</strong> (Float) - The closing price of the current candle</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Most commonly used node for price data. The closing price is often used for moving averages, trend analysis, and as a reference point for order execution.</p>
            </div>
          </div>
        </div>

        <!-- Get High -->
        <div class="node-doc" id="get/high">
          <h3>Get High <span class="node-type">get/high</span></h3>
          <p>Extracts the highest price from the current candle/bar data.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node reads directly from the current market data row.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>high</strong> (Float) - The highest price of the current candle</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Used for breakout strategies, resistance level identification, and stop-loss calculations. Essential for analyzing price action and volatility.</p>
            </div>
          </div>
        </div>

        <!-- Get Low -->
        <div class="node-doc" id="get/low">
          <h3>Get Low <span class="node-type">get/low</span></h3>
          <p>Extracts the lowest price from the current candle/bar data.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node reads directly from the current market data row.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>low</strong> (Float) - The lowest price of the current candle</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Used for support level identification, breakdown strategies, and stop-loss calculations. Important for risk management and entry point determination.</p>
            </div>
          </div>
        </div>

        <!-- Get Volume -->
        <div class="node-doc" id="get/volume">
          <h3>Get Volume <span class="node-type">get/volume</span></h3>
          <p>Extracts the trading volume from the current candle/bar data.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node reads directly from the current market data row.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>volume</strong> (Float) - The trading volume of the current candle</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Volume analysis for confirming price movements, identifying accumulation/distribution patterns, and volume-based indicators like Volume Weighted Average Price (VWAP).</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Set Value Nodes -->
      <section class="node-section" id="set-values">
        <h2>Set Value Nodes</h2>
        
        <!-- Set Float -->
        <div class="node-doc" id="set/float">
          <h3>Set Float <span class="node-type">set/float</span></h3>
          <p>Provides a constant floating-point number value.</p>
          <div class="node-details">
            <div class="properties">
              <h4>Properties</h4>
              <ul>
                <li><strong>value</strong> (Float) - The constant float value to output (default: 1.0)</li>
              </ul>
            </div>
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node outputs a constant value.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Float</strong> (Float) - The configured constant value</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Used for providing constants in calculations, such as multipliers, thresholds, or fixed parameters for indicators and trading logic.</p>
            </div>
          </div>
        </div>

        <!-- Set Integer -->
        <div class="node-doc" id="set/integer">
          <h3>Set Integer <span class="node-type">set/integer</span></h3>
          <p>Provides a constant integer value.</p>
          <div class="node-details">
            <div class="properties">
              <h4>Properties</h4>
              <ul>
                <li><strong>value</strong> (Integer) - The constant integer value to output (default: 1)</li>
              </ul>
            </div>
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node outputs a constant value.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Integer</strong> (Integer) - The configured constant value</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Commonly used for setting periods in indicators (e.g., 20 for a 20-period moving average), quantity values, or counting operations.</p>
            </div>
          </div>
        </div>

        <!-- Set String -->
        <div class="node-doc" id="set/string">
          <h3>Set String <span class="node-type">set/string</span></h3>
          <p>Provides a constant string value.</p>
          <div class="node-details">
            <div class="properties">
              <h4>Properties</h4>
              <ul>
                <li><strong>value</strong> (String) - The constant string value to output (default: '')</li>
              </ul>
            </div>
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node outputs a constant value.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>String</strong> (String) - The configured constant value</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Used for messages, labels, symbol names, or any text-based parameters in your trading strategy.</p>
            </div>
          </div>
        </div>

        <!-- Set Bool -->
        <div class="node-doc" id="set/bool">
          <h3>Set Bool <span class="node-type">set/bool</span></h3>
          <p>Provides a constant boolean value.</p>
          <div class="node-details">
            <div class="properties">
              <h4>Properties</h4>
              <ul>
                <li><strong>value</strong> (Boolean) - The constant boolean value to output (default: false)</li>
              </ul>
            </div>
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node outputs a constant value.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Bool</strong> (Boolean) - The configured constant value</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Used for enabling/disabling features, setting flags, or providing boolean inputs to logical operations.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Math Operations -->
      <section class="node-section" id="math-operations">
        <h2>Math Operations</h2>
        
        <!-- Multiply Float -->
        <div class="node-doc" id="math/multiply_float">
          <h3>Multiply Float <span class="node-type">math/multiply_float</span></h3>
          <p>Multiplies two floating-point numbers.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (Float) - First number</li>
                <li><strong>1</strong> (Float) - Second number</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Float</strong> (Float) - Result of multiplication (a × b)</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Used for calculating position sizes, applying multipliers to prices, or scaling values in mathematical operations.</p>
            </div>
          </div>
        </div>

        <!-- Add Float -->
        <div class="node-doc" id="math/add_float">
          <h3>Add Float <span class="node-type">math/add_float</span></h3>
          <p>Adds two floating-point numbers.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (Float) - First number</li>
                <li><strong>1</strong> (Float) - Second number</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Float</strong> (Float) - Result of addition (a + b)</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Used for calculating total values, adding offsets to prices, or combining multiple numeric inputs.</p>
            </div>
          </div>
        </div>

        <!-- Divide Float -->
        <div class="node-doc" id="math/divide_float">
          <h3>Divide Float <span class="node-type">math/divide_float</span></h3>
          <p>Divides two floating-point numbers.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (Float) - Dividend (number to be divided)</li>
                <li><strong>1</strong> (Float) - Divisor (number to divide by)</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Float</strong> (Float) - Result of division (a ÷ b)</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Used for calculating ratios, percentages, or average values. Returns null if division by zero is attempted.</p>
            </div>
            <div class="notes">
              <h4>Notes</h4>
              <p><strong>⚠️ Warning:</strong> Division by zero will result in null output and log an error.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Technical Indicators -->
      <section class="node-section" id="indicators">
        <h2>Technical Indicators</h2>
        
        <!-- Moving Average -->
        <div class="node-doc" id="indicators/ma">
          <h3>Moving Average <span class="node-type">indicators/ma</span></h3>
          <p>Calculates moving averages (Simple MA or Exponential MA) over a specified period.</p>
          <div class="node-details">
            <div class="properties">
              <h4>Properties</h4>
              <ul>
                <li><strong>ma_type</strong> (String) - Type of moving average: 'sma' for Simple MA, 'ema' for Exponential MA (default: 'ema')</li>
              </ul>
            </div>
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (Float) - Price value (typically close price)</li>
                <li><strong>1</strong> (Integer) - Period/Window size for the moving average</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Float</strong> (Float) - Calculated moving average value</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Essential for trend analysis, support/resistance identification, and creating crossover strategies. EMA reacts faster to price changes than SMA.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Comparison Nodes -->
      <section class="node-section" id="comparisons">
        <h2>Comparison Operations</h2>
        
        <!-- Cross Over -->
        <div class="node-doc" id="compare/cross_over">
          <h3>Cross Over <span class="node-type">compare/cross_over</span></h3>
          <p>Detects when the first input crosses above the second input.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (Float) - First value (e.g., fast moving average)</li>
                <li><strong>1</strong> (Float) - Second value (e.g., slow moving average)</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Condition</strong> (Boolean) - True when first input crosses above second input</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Common for bullish signal detection, such as when a fast MA crosses above a slow MA, or when price crosses above a resistance level.</p>
            </div>
          </div>
        </div>

        <!-- Cross Under -->
        <div class="node-doc" id="compare/cross_under">
          <h3>Cross Under <span class="node-type">compare/cross_under</span></h3>
          <p>Detects when the first input crosses below the second input.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (Float) - First value (e.g., fast moving average)</li>
                <li><strong>1</strong> (Float) - Second value (e.g., slow moving average)</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Condition</strong> (Boolean) - True when first input crosses below second input</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Common for bearish signal detection, such as when a fast MA crosses below a slow MA, or when price crosses below a support level.</p>
            </div>
          </div>
        </div>

                 <!-- Greater Than -->
         <div class="node-doc" id="compare/greater">
           <h3>Greater Than <span class="node-type">compare/greater</span></h3>
           <p>Compares if the first input is greater than the second input.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (Float) - First value</li>
                 <li><strong>1</strong> (Float) - Second value</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>Bool</strong> (Boolean) - True if first input > second input</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Used for threshold checks, price level comparisons, and conditional logic in trading strategies.</p>
             </div>
           </div>
         </div>

         <!-- Less Than -->
         <div class="node-doc" id="compare/smaller">
           <h3>Less Than <span class="node-type">compare/smaller</span></h3>
           <p>Compares if the first input is less than the second input.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (Float) - First value</li>
                 <li><strong>1</strong> (Float) - Second value</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>Bool</strong> (Boolean) - True if first input < second input</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Used for threshold checks, support level detection, and stop-loss conditions in trading strategies.</p>
             </div>
           </div>
         </div>

         <!-- Equal To -->
         <div class="node-doc" id="compare/equal">
           <h3>Equal To <span class="node-type">compare/equal</span></h3>
           <p>Compares if two inputs are exactly equal.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (Any) - First value</li>
                 <li><strong>1</strong> (Any) - Second value</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>Bool</strong> (Boolean) - True if inputs are equal</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Used for exact value matching, state checks, or comparing specific price levels or indicator values.</p>
             </div>
           </div>
         </div>
      </section>

      <!-- Logic Operations -->
      <section class="node-section" id="logic">
        <h2>Logic Operations</h2>
        
        <!-- AND -->
        <div class="node-doc" id="logic/and">
          <h3>AND <span class="node-type">logic/and</span></h3>
          <p>Logical AND operation - returns true only if both inputs are true.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (Boolean) - First condition</li>
                <li><strong>1</strong> (Boolean) - Second condition</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Bool</strong> (Boolean) - True if both inputs are true</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Essential for combining multiple conditions, such as requiring both a bullish crossover AND volume above average for a buy signal.</p>
            </div>
          </div>
        </div>

                 <!-- OR -->
         <div class="node-doc" id="logic/or">
           <h3>OR <span class="node-type">logic/or</span></h3>
           <p>Logical OR operation - returns true if either input is true.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (Boolean) - First condition</li>
                 <li><strong>1</strong> (Boolean) - Second condition</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>Bool</strong> (Boolean) - True if either input is true</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Used when you want to trigger actions if any of multiple conditions are met, such as multiple entry signals or alternative exit conditions.</p>
             </div>
           </div>
         </div>

         <!-- NOT -->
         <div class="node-doc" id="logic/not">
           <h3>NOT <span class="node-type">logic/not</span></h3>
           <p>Logical NOT operation - inverts the boolean input.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (Boolean) - Condition to invert</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>Bool</strong> (Boolean) - Inverted input value</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Used to invert conditions, such as detecting when a condition is NOT met or creating opposite signals.</p>
             </div>
           </div>
         </div>

         <!-- IF Condition -->
         <div class="node-doc" id="logic/if">
           <h3>IF Condition <span class="node-type">logic/if</span></h3>
           <p>Conditional execution node that routes signals based on a boolean condition.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (Boolean) - Condition to evaluate</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>True</strong> (String) - Outputs "GO" if condition is true</li>
                 <li><strong>False</strong> (String) - Outputs "GO" if condition is false</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Controls execution flow in strategies. Connect the appropriate output to different trading actions based on market conditions.</p>
             </div>
           </div>
         </div>
      </section>

      <!-- Trading Operations -->
      <section class="node-section" id="trading">
        <h2>Trading Operations</h2>
        
        <!-- Create Order -->
        <div class="node-doc" id="trade/create_order">
          <h3>Create Order <span class="node-type">trade/create_order</span></h3>
          <p>Creates market or limit orders for buying or selling with automatic parameter adjustment and dual-mode execution.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (Exec) - Trigger signal ("GO" to execute, any other value is ignored)</li>
                <li><strong>1</strong> (Bool) - Direction (true = BUY, false = SELL)</li>
                <li><strong>2</strong> (Bool) - Order type (true = LIMIT, false = MARKET)</li>
                <li><strong>3</strong> (Float) - Price (required for limit orders, ignored for market orders)</li>
                <li><strong>4</strong> (Float) - Quantity (automatically made positive if negative)</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>ID</strong> (String) - Order ID (local format: "local_{seq}_{timestamp}" or remote Bybit ID in live mode)</li>
                <li><strong>Exec</strong> (Exec) - "GO" when order is successfully created, null otherwise</li>
              </ul>
            </div>
            <div class="behavior">
              <h4>Execution Behavior</h4>
              <ul>
                <li><strong>Trigger Logic:</strong> Only executes when input 0 equals "GO". Preserves last order ID on other triggers.</li>
                <li><strong>Parameter Validation:</strong> Returns null if direction, order type, or quantity inputs are missing</li>
                <li><strong>Quantity Handling:</strong> Automatically converts negative quantities to positive values</li>
                <li><strong>Price Adjustment:</strong> Uses current candle's close price for market orders</li>
                <li><strong>Exchange Compliance:</strong> Automatically adjusts quantity and price to meet instrument specifications (min_order_qty, qty_step, tick_size)</li>
              </ul>
            </div>
            <div class="modes">
              <h4>Mode-Specific Behavior</h4>
              <ul>
                <li><strong>Backtest Mode:</strong> Creates local order record, logs order creation, simulates immediate execution for market orders</li>
                <li><strong>Live Mode:</strong> Sends API request to Bybit with 3-attempt retry logic, handles both local and remote order IDs</li>
              </ul>
            </div>
            <div class="order-tracking">
              <h4>Order Management</h4>
              <ul>
                <li><strong>Local ID Format:</strong> "local_{counter}_{timestamp_ms}" (e.g., "local_1_1682000000123")</li>
                <li><strong>Remote ID:</strong> Bybit's orderId returned from successful API calls</li>
                <li><strong>Order Status:</strong> 'open' for successful creation, 'error' for failed API calls</li>
                <li><strong>Execution Time:</strong> Set immediately for market orders, null for limit orders until filled</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Primary order creation node for all trading strategies. Handles both entry and exit orders with robust error handling and exchange compliance.</p>
            </div>
          </div>
        </div>

        <!-- Get Position -->
        <div class="node-doc" id="trade/get_position">
          <h3>Get Position <span class="node-type">trade/get_position</span></h3>
          <p>Retrieves current position information (quantity, average price, creation time).</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <p>None - This node reads current position state.</p>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Price</strong> (Float) - Average entry price (null if no position)</li>
                <li><strong>Quantity</strong> (Float) - Net position size (positive = long, negative = short, 0 = flat)</li>
                <li><strong>Created</strong> (Timestamp) - When the position was opened</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Essential for position-aware strategies, risk management, and calculating unrealized P&L. Uses FIFO accounting for position calculation.</p>
            </div>
          </div>
        </div>

                                   <!-- Create Conditional Order -->
          <div class="node-doc" id="trade/create_conditional_order">
            <h3>Create Conditional Order <span class="node-type">trade/create_conditional_order</span></h3>
            <p>Creates conditional/stop orders that become market orders when price reaches the specified trigger level.</p>
            <div class="node-details">
              <div class="inputs">
                <h4>Inputs</h4>
                <ul>
                  <li><strong>0</strong> (Exec) - Trigger signal ("GO" to execute, any other value is ignored)</li>
                  <li><strong>1</strong> (Bool) - Direction (true = BUY, false = SELL)</li>
                  <li><strong>2</strong> (Float) - Trigger price level (price at which order activates)</li>
                  <li><strong>3</strong> (Float) - Quantity (automatically made positive if negative)</li>
                </ul>
              </div>
              <div class="outputs">
                <h4>Outputs</h4>
                <ul>
                  <li><strong>ID</strong> (String) - Order ID (local format: "local_{seq}_{timestamp}" or remote Bybit ID in live mode)</li>
                  <li><strong>Exec</strong> (Exec) - "GO" when order is successfully created, null otherwise</li>
                </ul>
              </div>
              <div class="behavior">
                <h4>Execution Behavior</h4>
                <ul>
                  <li><strong>Trigger Logic:</strong> Only executes when input 0 equals "GO". Preserves last order ID on other triggers.</li>
                  <li><strong>Parameter Validation:</strong> Returns null if direction, trigger price, or quantity inputs are missing</li>
                  <li><strong>Quantity Handling:</strong> Automatically converts negative quantities to positive values</li>
                  <li><strong>Exchange Compliance:</strong> Automatically adjusts quantity and trigger price to meet instrument specifications</li>
                  <li><strong>Order Type:</strong> Always creates market orders that execute when trigger price is hit</li>
                </ul>
              </div>
              <div class="trigger-logic">
                <h4>Trigger Mechanism</h4>
                <ul>
                  <li><strong>BUY Orders:</strong> Trigger when current high price >= trigger price (breakout above)</li>
                  <li><strong>SELL Orders:</strong> Trigger when current low price <= trigger price (breakdown below)</li>
                  <li><strong>Backtest Simulation:</strong> Checks trigger conditions on each candle using high/low prices</li>
                  <li><strong>Live Trading:</strong> Bybit exchange monitors trigger conditions in real-time</li>
                </ul>
              </div>
              <div class="modes">
                <h4>Mode-Specific Behavior</h4>
                <ul>
                  <li><strong>Backtest Mode:</strong> Creates order with 'conditional' category, simulates trigger logic</li>
                  <li><strong>Live Mode:</strong> Sends conditional order to Bybit with triggerDirection parameter (1=Buy, 2=Sell)</li>
                </ul>
              </div>
              <div class="usage">
                <h4>Usage</h4>
                <p>Essential for breakout strategies, stop-losses, take-profits, and entry orders at specific price levels. Automatically becomes a market order when triggered.</p>
              </div>
              <div class="notes">
                <h4>Important Notes</h4>
                <ul>
                  <li><strong>⚠️ Market Order Execution:</strong> Becomes a market order when triggered - no price control after activation</li>
                  <li><strong>🎯 Trigger Direction:</strong> BUY orders trigger on upward price movement, SELL orders on downward movement</li>
                  <li><strong>⏰ No Execution Time:</strong> time_executed remains null until trigger conditions are met</li>
                </ul>
              </div>
            </div>
          </div>

         <!-- Cancel Order -->
         <div class="node-doc" id="trade/cancel_order">
           <h3>Cancel Order <span class="node-type">trade/cancel_order</span></h3>
           <p>Cancels a specific order by its ID.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (String) - Trigger signal ("GO" to execute)</li>
                 <li><strong>1</strong> (String) - Order ID to cancel</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>Exec</strong> (String) - Execution confirmation ("GO" when cancelled)</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Precise order management for cancelling specific orders when conditions change or timeout periods are reached.</p>
             </div>
           </div>
         </div>

         <!-- Cancel All Orders -->
         <div class="node-doc" id="trade/cancel_all_order">
           <h3>Cancel All Orders <span class="node-type">trade/cancel_all_order</span></h3>
           <p>Cancels all open orders for the current symbol.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (String) - Trigger signal ("GO" to execute)</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>Exec</strong> (String) - Execution confirmation ("GO" when completed)</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Risk management tool for quickly closing all pending orders, often used during market volatility or strategy changes.</p>
             </div>
           </div>
         </div>

         <!-- Modify Order -->
         <div class="node-doc" id="trade/modify_order">
           <h3>Modify Order <span class="node-type">trade/modify_order</span></h3>
           <p>Modifies the price and/or quantity of an existing order.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (String) - Trigger signal ("GO" to execute)</li>
                 <li><strong>1</strong> (String) - Order ID to modify</li>
                 <li><strong>2</strong> (Float) - New price (null to keep current)</li>
                 <li><strong>3</strong> (Float) - New quantity (null to keep current)</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>ID</strong> (String) - Order ID</li>
                 <li><strong>Exec</strong> (String) - Execution confirmation ("GO" when modified)</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Dynamic order management to adjust prices based on market conditions or change quantities based on risk parameters.</p>
             </div>
           </div>
         </div>

         <!-- Get Order -->
         <div class="node-doc" id="trade/get_order">
           <h3>Get Order <span class="node-type">trade/get_order</span></h3>
           <p>Retrieves information about a specific order by its ID and provides execution signals.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (String) - Order ID to query</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>ID</strong> (String) - Order ID</li>
                 <li><strong>Price</strong> (Float) - Order price</li>
                 <li><strong>Quantity</strong> (Float) - Order quantity</li>
                 <li><strong>Created</strong> (Float) - Minutes since order creation</li>
                 <li><strong>Executed?</strong> (Exec) - Outputs "GO" only once when order gets executed, null otherwise</li>
                 <li><strong>Open?</strong> (Boolean) - True if order is still open/pending</li>
               </ul>
             </div>
             <div class="execution-logic">
               <h4>Execution Detection</h4>
               <ul>
                 <li><strong>One-Time Signal:</strong> "Executed?" outputs "GO" only on the exact candle when execution occurs</li>
                 <li><strong>Subsequent Calls:</strong> Returns null for "Executed?" after the initial execution signal</li>
                 <li><strong>Status Tracking:</strong> Monitors order status changes between open/executed/cancelled states</li>
                 <li><strong>Live Mode:</strong> Queries exchange API for real-time order status updates</li>
                 <li><strong>Backtest Mode:</strong> Uses internal order state tracking and execution simulation</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Essential for order-dependent logic, execution confirmations, and timeout strategies. Connect "Executed?" output to trigger follow-up actions exactly once when orders fill.</p>
             </div>
           </div>
         </div>

         <!-- Get Last Order -->
         <div class="node-doc" id="trade/get_last_order">
           <h3>Get Last Order <span class="node-type">trade/get_last_order</span></h3>
           <p>Retrieves information about the most recently created order.</p>
           <div class="node-details">
             <div class="inputs">
               <h4>Inputs</h4>
               <p>None - This node reads the last order from memory.</p>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <ul>
                 <li><strong>ID</strong> (String) - Last order ID</li>
                 <li><strong>Long/Short</strong> (Boolean) - Order direction (true = BUY, false = SELL)</li>
                 <li><strong>Normal/Conditional</strong> (Boolean) - Order type (true = limit, false = market/conditional)</li>
                 <li><strong>Cancelled</strong> (Boolean) - True if the order was cancelled</li>
               </ul>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Quick access to the most recent order for status checks, follow-up actions, or order sequence management.</p>
             </div>
           </div>
         </div>
      </section>

      <!-- Chart Tools -->
      <section class="node-section" id="tools">
        <h2>Chart Tools</h2>
        
                 <!-- Add Indicator -->
         <div class="node-doc" id="tools/add_indicator">
           <h3>Add Indicator <span class="node-type">tools/add_indicator</span></h3>
           <p>Adds a custom indicator series to the chart for visualization.</p>
           <div class="node-details">
             <div class="properties">
               <h4>Properties</h4>
               <ul>
                 <li><strong>name</strong> (String) - Name of the indicator series</li>
               </ul>
             </div>
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (Float) - Value to add to the series</li>
                 <li><strong>1</strong> (String) - Optional runtime name override</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <p>None - This node adds data directly to the chart without producing outputs for connection to other nodes.</p>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Visualize custom calculations, moving averages, or any numeric series on the trading chart for analysis and debugging. The indicator appears as a line series on the chart.</p>
             </div>
           </div>
         </div>

                 <!-- Add Signal -->
         <div class="node-doc" id="tools/add_signal">
           <h3>Add Signal <span class="node-type">tools/add_signal</span></h3>
           <p>Adds visual markers/signals to the chart when conditions are met.</p>
           <div class="node-details">
             <div class="properties">
               <h4>Properties</h4>
               <ul>
                 <li><strong>name</strong> (String) - Name/text for the signal marker</li>
               </ul>
             </div>
             <div class="inputs">
               <h4>Inputs</h4>
               <ul>
                 <li><strong>0</strong> (Boolean) - Signal condition (true to place marker)</li>
                 <li><strong>1</strong> (String) - Optional runtime name override</li>
               </ul>
             </div>
             <div class="outputs">
               <h4>Outputs</h4>
               <p>None - This node adds markers directly to the chart without producing outputs for connection to other nodes.</p>
             </div>
             <div class="usage">
               <h4>Usage</h4>
               <p>Mark entry/exit points, alerts, or any significant events on the chart for visual analysis and strategy validation. Markers appear as visual indicators on the chart at the corresponding timestamps.</p>
             </div>
           </div>
         </div>
      </section>

      <!-- Communication -->
      <section class="node-section" id="communication">
        <h2>Communication</h2>
        
        <!-- Send Telegram Message -->
        <div class="node-doc" id="telegram/send_message">
          <h3>Send Telegram Message <span class="node-type">telegram/send_message</span></h3>
          <p>Sends notifications via Telegram bot when triggered.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (String) - Trigger signal ("GO" to send)</li>
                <li><strong>1</strong> (String) - Message text to send</li>
                <li><strong>2</strong> (String) - Telegram user/chat ID</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>Exec</strong> (Boolean) - True if message sent successfully</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Real-time notifications for trade executions, alerts, or important market events. Requires Telegram bot token configuration.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Utilities -->
      <section class="node-section" id="utilities">
        <h2>Utilities</h2>
        
        <!-- Is None Check -->
        <div class="node-doc" id="trade/is_none">
          <h3>Is None Check <span class="node-type">trade/is_none</span></h3>
          <p>Checks if an input value is null/None.</p>
          <div class="node-details">
            <div class="inputs">
              <h4>Inputs</h4>
              <ul>
                <li><strong>0</strong> (Any) - Value to check for null</li>
              </ul>
            </div>
            <div class="outputs">
              <h4>Outputs</h4>
              <ul>
                <li><strong>None?</strong> (Boolean) - True if input is null/None</li>
              </ul>
            </div>
            <div class="usage">
              <h4>Usage</h4>
              <p>Data validation and error handling in complex strategies. Useful for checking if indicators have sufficient data or if orders exist.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

// Node categories for sidebar navigation
const nodeCategories = ref([
  {
    name: 'data-access',
    displayName: 'Data Access',
    expanded: true,
    nodes: [
      { type: 'get/open', name: 'Get Open' },
      { type: 'get/close', name: 'Get Close' },
      { type: 'get/high', name: 'Get High' },
      { type: 'get/low', name: 'Get Low' },
      { type: 'get/volume', name: 'Get Volume' }
    ]
  },
  {
    name: 'set-values',
    displayName: 'Set Values',
    expanded: false,
    nodes: [
      { type: 'set/float', name: 'Set Float' },
      { type: 'set/integer', name: 'Set Integer' },
      { type: 'set/string', name: 'Set String' },
      { type: 'set/bool', name: 'Set Bool' }
    ]
  },
  {
    name: 'math-operations',
    displayName: 'Math Operations',
    expanded: false,
    nodes: [
      { type: 'math/multiply_float', name: 'Multiply Float' },
      { type: 'math/add_float', name: 'Add Float' },
      { type: 'math/divide_float', name: 'Divide Float' }
    ]
  },
  {
    name: 'indicators',
    displayName: 'Technical Indicators',
    expanded: false,
    nodes: [
      { type: 'indicators/ma', name: 'Moving Average' }
    ]
  },
  {
    name: 'comparisons',
    displayName: 'Comparisons',
    expanded: false,
    nodes: [
      { type: 'compare/cross_over', name: 'Cross Over' },
      { type: 'compare/cross_under', name: 'Cross Under' },
      { type: 'compare/greater', name: 'Greater Than' },
      { type: 'compare/smaller', name: 'Less Than' },
      { type: 'compare/equal', name: 'Equal To' }
    ]
  },
  {
    name: 'logic',
    displayName: 'Logic Operations',
    expanded: false,
    nodes: [
      { type: 'logic/and', name: 'AND' },
      { type: 'logic/or', name: 'OR' },
      { type: 'logic/not', name: 'NOT' },
      { type: 'logic/if', name: 'IF Condition' }
    ]
  },
  {
    name: 'trading',
    displayName: 'Trading Operations',
    expanded: false,
    nodes: [
      { type: 'trade/create_order', name: 'Create Order' },
      { type: 'trade/create_conditional_order', name: 'Create Conditional Order' },
      { type: 'trade/cancel_order', name: 'Cancel Order' },
      { type: 'trade/cancel_all_order', name: 'Cancel All Orders' },
      { type: 'trade/modify_order', name: 'Modify Order' },
      { type: 'trade/get_position', name: 'Get Position' },
      { type: 'trade/get_order', name: 'Get Order' },
      { type: 'trade/get_last_order', name: 'Get Last Order' }
    ]
  },
  {
    name: 'tools',
    displayName: 'Chart Tools',
    expanded: false,
    nodes: [
      { type: 'tools/add_indicator', name: 'Add Indicator' },
      { type: 'tools/add_signal', name: 'Add Signal' }
    ]
  },
  {
    name: 'communication',
    displayName: 'Communication',
    expanded: false,
    nodes: [
      { type: 'telegram/send_message', name: 'Send Telegram Message' }
    ]
  },
  {
    name: 'utilities',
    displayName: 'Utilities',
    expanded: false,
    nodes: [
      { type: 'trade/is_none', name: 'Is None Check' }
    ]
  }
])

const activeNode = ref('')

// Toggle category expansion
const toggleCategory = (categoryName: string) => {
  const category = nodeCategories.value.find(c => c.name === categoryName)
  if (category) {
    category.expanded = !category.expanded
  }
}

// Scroll to specific node documentation
const scrollToNode = (nodeType: string) => {
  activeNode.value = nodeType
  const element = document.getElementById(nodeType)
  if (element) {
    const yOffset = -20; // Add some offset from the top
    const y = element.getBoundingClientRect().top + window.pageYOffset + yOffset
    window.scrollTo({ top: y, behavior: 'smooth' })
  }
}

// Handle scroll to update active node
const handleScroll = () => {
  const sections = document.querySelectorAll('.node-doc')
  let current = ''
  
  sections.forEach((section) => {
    const rect = section.getBoundingClientRect()
    if (rect.top <= 100) {
      current = section.id
    }
  })
  
  activeNode.value = current
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.docs-container {
  display: flex;
  min-height: 100vh;
  background-color: var(--color-background);
}

.docs-sidebar {
  width: 280px;
  background: var(--color-background-soft);
  border-right: 1px solid var(--color-border);
  position: fixed;
  height: 100vh;
  overflow-y: auto;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.3);
}

.sidebar-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: #222222;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #fff;
}

.sidebar-content {
  padding: 1rem 0;
}

.node-category {
  margin-bottom: 0.5rem;
}

.category-title {
  display: flex;
  align-items: center;
  padding: 0.75rem 1.5rem;
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  transition: background-color 0.2s;
}

.category-title:hover {
  background-color: #353535;
}

.category-title i {
  margin-right: 0.5rem;
  font-size: 0.75rem;
  color: #ccc;
}

.node-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.node-list li {
  padding: 0.5rem 2.5rem;
  font-size: 0.85rem;
  color: #ccc;
  cursor: pointer;
  transition: all 0.2s;
}

.node-list li:hover {
  background-color: #353535;
  color: #fff;
}

.node-list li.active {
  background-color: #222222;
  color: #b0e0ff;
  font-weight: 500;
  border-left: 3px solid #b0e0ff;
  margin-left: -3px;
}

.docs-content {
  margin-left: 280px;
  flex: 1;
  padding: 2rem 3rem;
  max-width: calc(100vw - 280px);
  background: var(--color-background);
  width: 100%;
}

@media (min-width: 1400px) {
  .docs-content {
    max-width: 1200px;
    margin-left: calc(280px + (100vw - 1480px) / 2);
  }
}

@media (max-width: 768px) {
  .docs-sidebar {
    width: 260px;
  }
  
  .docs-content {
    margin-left: 260px;
    padding: 1.5rem;
    max-width: calc(100vw - 260px);
  }
  
  .node-doc {
    padding: 1.5rem;
  }
}

@media (max-width: 480px) {
  .docs-sidebar {
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }
  
  .docs-content {
    margin-left: 0;
    padding: 1rem;
    max-width: 100vw;
  }
}

.content-header {
  margin-bottom: 3rem;
  max-width: 100%;
}

.content-header h1 {
  font-size: 2.5rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 0.5rem;
}

.content-header p {
  font-size: 1.1rem;
  color: #ccc;
}

.node-section {
  margin-bottom: 4rem;
}

.node-section h2 {
  font-size: 1.8rem;
  font-weight: 600;
  color: #fff;
  margin-bottom: 2rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--color-border);
}

.node-doc {
  background: var(--color-background-soft);
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  border-left: 4px solid #b0e0ff;
  border: 1px solid var(--color-border);
  max-width: 100%;
}

.node-doc h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #fff;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.node-type {
  background: #222222;
  color: #b0e0ff;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  font-family: 'Courier New', monospace;
  border: 1px solid #b0e0ff;
}

.node-doc > p {
  font-size: 1rem;
  color: #ccc;
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.node-details > div {
  margin-bottom: 1.5rem;
}

.node-details h4 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #fff;
  margin-bottom: 0.75rem;
}

.node-details ul {
  list-style: none;
  padding: 0;
}

.node-details li {
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border);
}

.node-details li:last-child {
  border-bottom: none;
}

.node-details strong {
  color: #b0e0ff;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

.usage p, .notes p {
  line-height: 1.6;
  color: #ccc;
}

.notes {
  background: rgba(255, 85, 85, 0.1);
  border: 1px solid #F77;
  border-radius: 6px;
  padding: 1rem;
}

.load-more {
  text-align: center;
  padding: 2rem;
  color: #718096;
  font-style: italic;
}

.overview-section {
  background: var(--color-background-soft);
  border-radius: 8px;
  padding: 2rem;
  margin: 2rem 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  border-left: 4px solid #d2ffb0;
  border: 1px solid var(--color-border);
}

.overview-section h2 {
  color: #fff;
  margin-bottom: 1rem;
  font-size: 1.5rem;
}

.overview-section h3 {
  color: #fff;
  margin: 1.5rem 0 0.75rem 0;
  font-size: 1.2rem;
}

.quick-start ul, .modes-info ul, .data-types ul, .execution-model ul {
  margin: 0.75rem 0;
  padding-left: 1.5rem;
}

.quick-start li, .modes-info li, .data-types li, .execution-model li {
  margin: 0.5rem 0;
  line-height: 1.5;
  color: #ccc;
}

.quick-start strong, .modes-info strong, .data-types strong, .execution-model strong {
  color: #d2ffb0;
  font-weight: 600;
}

.data-type-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  margin-right: 0.5rem;
  vertical-align: middle;
}
</style>
