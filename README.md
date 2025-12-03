# Solar PV Performance Analytics Chatbot

A Streamlit-powered chatbot for querying and analyzing solar farm performance data using RAG and AI agents.  
It supports natural language questions about energy output, performance ratio, weather metrics, and more.

<img width="1530" height="716" alt="image" src="https://github.com/user-attachments/assets/18a2c66e-d877-4ac1-b5a8-1bd9c72585bf" />
<img width="1484" height="703" alt="image" src="https://github.com/user-attachments/assets/0fe34293-f3a5-4cb1-a972-111054e3543f" />
<img width="1444" height="673" alt="image" src="https://github.com/user-attachments/assets/c67f38f0-3526-4fe4-9368-76b2a2736b67" />




## Directory Structure
solar_chatbot/
│
├── app.py                      # Main Streamlit app and UI logic
├── agents.py                   # AI agent definitions, tools, and prompt logic
├── prompts.py                  # Prompt templates for SQL and answer agents
├── db.py                       # DuckDB connection and query management
├── get_data.py                 # Data preprocessing and metric calculation functions
├── styles.css                  # Custom CSS for UI (optional)
├── .env                        # Environment variables (optional)
├── 5-Site_DG-PV1-DB-DG-M1A.csv # Raw solar farm data (not included)
└── README.md                   # This documentation

## Data Source
[Desert Knowledge Australia Solar Centre](https://dkasolarcentre.com.au/download?location=yulara)
Desert Gardens (Site 1) - 1,058.4 kW poly-Si fixed-tilt system 

## How It Works

- **Data Loading:**  
  `get_data.py` loads and preprocesses solar farm data from CSV, cleans it, and computes derived metrics.

- **Database:**  
  `db.py` loads the cleaned data into a DuckDB table for fast SQL querying.

- **AI Agents:**  
  `agents.py` defines two agents:
  - **SQL Agent:** Converts user questions to safe, read-only SQL queries.
  - **Answer Agent:** Summarizes SQL results in natural language.

- **Metric Tools:**  
  Functions for total energy, specific yield, and temperature-corrected performance ratio are exposed as agent tools.

- **Prompt Engineering:**  
  `prompts.py` provides detailed instructions and mappings so the AI understands domain terms and how to compute metrics.

- **Streamlit UI:**  
  `app.py` provides a chat-like interface for asking questions, viewing SQL, table results, and downloading data.

## Features & Techniques

- **Natural Language to SQL:**  
  Ask questions like "What is the average daily production in June 2024?" and get answers.

- **Safe Querying:**  
  Only SELECT queries are allowed; destructive SQL is blocked.

- **Metric Computation:**  
  Supports aggregated metrics (hourly, daily, monthly, yearly), peak power, specific yield, and temperature-corrected PR.

- **Domain Mapping:**  
  The AI can map domain terms (e.g., "PR") to the correct calculation, even if not a direct column.

- **Downloadable Results:**  
  Export results as CSV or JSON.

- **Customizable Prompts:**  
  Prompts guide the AI to use the correct columns, tools, and aggregation.

## Dependencies

- Python 3.8+
- [Streamlit](https://streamlit.io/)
- [DuckDB](https://duckdb.org/)
- [pandas](https://pandas.pydata.org/)
- [numpy](https://numpy.org/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [pydantic](https://docs.pydantic.dev/)
- [pydantic-ai](https://github.com/torchtw/pydantic-ai) (custom agent framework)

## Usage

1. **Prepare Data:**  
   Place your solar farm CSV file (e.g., `5-Site_DG-PV1-DB-DG-M1A.csv`) in the project directory.

2. **Run the App:**  
   streamlit run app.py

3. **Ask Questions:**  
   Use the chat interface to ask about energy output, performance ratio, weather metrics, etc.

4. **Download Results:**  
   Use the download buttons to export query results.

## Customization

- **Prompts:**  
  Edit `prompts.py` to adjust domain mappings or instructions.
- **Metric Tools:**  
  Extend `get_data.py` and `agents.py` to add new metrics or tools.
- **UI:**  
  Customize `styles.css` for branding.
