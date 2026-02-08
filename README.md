# Synapse_LLM

A framework for generating and testing algorithmic trading strategies using Large Language Models (LLMs).

## Overview

This project automates the process of:
1. Generating trading strategies using LLMs (OpenAI, Claude, or Gemini)
2. Converting strategy descriptions into executable Python code
3. Running backtests on the generated strategies
4. Organizing, analyzing, and ranking the results

## Project Structure

```
Synapse_LLM-1/
├── backtesting_agent/
│   ├── run_code.py         # Execution and logging infrastructure
│   ├── openai.py           # OpenAI API integration
│   ├── claude.py           # Claude API integration 
│   ├── gemini.py           # Gemini API integration
│   ├── prompts.py          # LLM prompts for strategy generation
│   └── extract_*.py        # Utilities for code extraction
├── tests.py                # Main execution script with threading
├── z.py                    # Results analysis and shortlisting
├── extracted_strategies.json # Database of strategy descriptions
├── WFO Outputs/            # Walk-forward optimization outputs
├── Multibacktest Outputs/  # Multiple backtest outputs
└── Hyperparameter Output/  # Parameter optimization outputs
```

## Core Workflow

### 1. Strategy Generation and Execution (tests.py)

The main script processes strategies with these steps:

```python
# Main execution
with concurrent.futures.ThreadPoolExecutor(max_workers=num_processes) as executor:
    futures = []
    for i, (strategy_id, strategy_data) in enumerate(list(strategies.items())[91:96], start=91):
        futures.append(executor.submit(process_strategy, strategy_id, strategy_data, i))
```

For each strategy:
- A strategy description is sent to the LLM
- Python code is generated and extracted
- The code is executed, with error handling and retries
- Results are saved and outputs are organized

### 2. Code Execution and Logging (run_code.py)

The framework executes code in isolated environments:

```python
def run_code(code):
    # Create unique execution environment
    thread_id = threading.get_ident()
    unique_id = uuid.uuid4().hex[:8]
    run_dir = temp_dir / f"run_{thread_id}_{unique_id}"
    
    # Execute code with output capture
    # ...
```

Features:
- Thread-safe execution with unique directories
- Isolated environments for each execution
- Comprehensive stdout and stderr logging
- Automatic cleanup after execution

### 3. Results Analysis and Shortlisting (zoomlisting.py)

After generating and testing strategies, high-quality strategies are identified:

```python
# Filter strategies by Sharpe Ratio
filtered_df = df[df['Sharpe Ratio'] > 0.1]
```

Features:
- Consolidates results from multiple backtest outputs
- Filters strategies by performance metrics
- Color-codes results based on Sharpe Ratio ranges
- Creates consolidated Excel reports

## Usage

1. **Setup environment variables**:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

2. **Run the main process**:
   ```bash
   python tests.py
   ```

3. **Analyze and shortlist results**:
   ```bash
   python zoomlisting.py
   ```

## Output Organization

The framework automatically organizes output folders:
- WFO outputs are moved to `WFO Outputs/`
- Multibacktest outputs go to `Multibacktest Outputs/`
- Hyperparameter optimization results go to `Hyperparameter Output/`

Each output folder is prefixed with the strategy ID for easy identification.

## Error Handling

The system includes robust error handling:
- Up to 5 retry attempts for failed strategies
- Error diagnosis and correction via LLM
- Comprehensive error logs in the output directory

## Performance Metrics

Strategies are evaluated based on:
- Sharpe Ratio (primary metric for shortlisting)
- Other metrics from backtest results

Results with Sharpe Ratio > 0.1 are considered for further analysis, with color-coded classification:
- Orange: 0.1-0.2
- Light green: 0.2-0.3
- Medium green: 0.3-0.4
- Dark green: 0.4-0.5
- Sharp green: ≥0.5

## Requirements

- Python 3.8+
- OpenAI API access
- Python packages: openai, pandas, numpy, openpyxl, tqdm, etc.

## License

[MIT License]
# Agentic_AI
