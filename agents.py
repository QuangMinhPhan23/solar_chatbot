import re
from dataclasses import dataclass
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from prompts import sys_prompt, answer_sys
from db import get_connection
from get_data import calculate_total_energy, calculate_specific_yield, calculate_temperature_corrected_pr


# Database configuration
TABLE = get_connection()
DATE_COL = "timestamp"
ROW_LIMIT = 50
ANSWER_ROWS_LIMIT = 200

MODEL_NAME = "gpt-5-mini"
AGENT_SPEC = f"openai:{MODEL_NAME}"

FORBIDDEN_SQL_KEYWORDS = (
    "delete","update","insert","alter","drop","truncate","create","replace","grant","revoke",
    "attach","detach","copy","load","export","pragma","call","vacuum","set",
)
DESTRUCTIVE_INTENT_WORDS = (
    "delete","remove","drop","truncate","update","insert","modify","change","alter","create",
    "add column","erase",
)

def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql

def is_user_intent_destructive(question: str) -> bool:
    q = question.lower()
    return any(w in q for w in DESTRUCTIVE_INTENT_WORDS)

def is_select_only(sql: str) -> bool:
    s = _strip_sql_comments(sql).strip().lower()
    if ";" in s:
        return False
    starts_ok = s.startswith("select") or s.startswith("with ")
    if not starts_ok:
        return False
    return not any(re.search(rf"\b{kw}\b", s) for kw in FORBIDDEN_SQL_KEYWORDS)

# ======================= SQL Agent =======================
class SQLResult(BaseModel):
    sql_query: str = Field(..., description="A valid SELECT query")

@dataclass
class Deps:
    conn: Any  # DatabaseConnection

sql_agent = Agent[Deps, SQLResult](AGENT_SPEC, output_type=SQLResult, deps_type=Deps)

@sql_agent.system_prompt
async def sql_system_prompt() -> str:
    base = sys_prompt(TABLE, DATE_COL)
    guard = (
        "\n\nCRITICAL RULES:\n"
        "- Only generate a single-statement SELECT (optionally WITH ... SELECT).\n"
        "- Never use DELETE/UPDATE/INSERT/ALTER/DROP/TRUNCATE/CREATE/PRAGMA/etc.\n"
        "- If the user asks to delete/modify/create data, do NOT comply; still output a harmless\n"
        "  SELECT like: SELECT 'refused' AS message WHERE 1=0.\n"
    )
    return base + guard

# ======================= NL Answer Agent =======================
class AnswerOut(BaseModel):
    final_answer: str = Field(
        ..., description="Natural-language answer based strictly on provided rows"
    )

answer_agent = Agent[None, AnswerOut](AGENT_SPEC, output_type=AnswerOut)

@answer_agent.system_prompt
async def sql_to_nl_prompt() -> str:
    return answer_sys()
# ======================= AU Tools =======================

answer_agent = Agent(
    AGENT_SPEC,
    system_prompt=(
        "You are a solar farms assistant. Use these tools:\n\n"
        "- execute_sql_query(query_description): Query the database for solar farm information.\n\n"
        "- get_total_energy(data, aggregation='default'): Calculate cumulative AC energy output.\n\n"
        "- get_specific_yield(data, P_STC=1058.4, aggregation='default'): Calculate Specific Yield (kWh/kWp).\n\n"
        "- get_temperature_corrected_pr(data, P_STC=1058.4, gamma=-0.004, aggregation='default'): Calculate Temperature-Corrected Performance Ratio (PR).\n\n"
        "For queries that needs tools:\n"
        "1. If user asks , first query the database to get details\n"
        "2. Use the retrieved data and aggregation (if needed) and pass to tools\n"
        "Be concise and factual."
    ),
    deps_type=Deps,
)

@answer_agent.tool
def execute_sql_query(ctx, query_description: str) -> str:
    """Tool: Execute SQL query to get film data from database."""
    try:
        # Generate SQL from description
        sql_res = sql_agent.run_sync(query_description, deps=ctx.deps)
        sql = sql_res.output.sql_query.strip().rstrip(";")
        
        if not is_select_only(sql):
            return "Error: Cannot execute non-SELECT queries"
        
        # Execute query
        df = ctx.deps.conn.execute(sql).fetchdf()
        
        if len(df) == 0:
            return "No data found for the query"
        
        # Return as JSON string
        return df.head(10).to_json(orient="records", date_format="iso")
    except Exception as e:
        return f"Error executing query: {str(e)}"
    
@answer_agent.tool
def get_total_energy(data, aggregation='default') -> Any:
    """
    Calculate cumulative AC energy output for the specified period.

    Parameters:
        data (DataFrame): The input data containing 'timestamp' and 'Active_Power'.
        aggregation (str): Aggregation level - 'default', 'hourly', 'daily', 'monthly', 'yearly'.

    Returns:
        float or DataFrame: Total energy in kWh, with breakdown if requested.
    """
    return calculate_total_energy(data, aggregation)

@answer_agent.tool
def get_specific_yield(data, P_STC=1058.4, aggregation='default'):
    """
    Calculate Specific Yield (kWh/kWp) for the specified period.

    Parameters:
        data (DataFrame): The input data containing 'timestamp' and 'Active_Power'.
         aggregation (str): Aggregation level - 'default', 'hourly', 'daily', 'monthly', 'yearly'.

    Returns:
        float or DataFrame: Specific Yield (kWh/kWp) for the time period, with breakdown if requested.
    """
    return calculate_specific_yield(data, P_STC, aggregation)

@answer_agent.tool
def get_temperature_corrected_pr(data, P_STC=1058.4, gamma=-0.004, aggregation='default'):
    """
    Calculate Temperature-Corrected Performance Ratio (PR) for the specified period.

    Parameters:
        data (DataFrame): Must include 'timestamp', 'Active_Power',
                          'Global_Horizontal_Radiation', and 'Weather_Temperature_Celsius'.
        P_STC (float): Rated DC capacity at STC (kW).
        gamma (float): Temperature coefficient (-0.004/°C for poly-Si).
        aggregation (str): 'default', 'hourly', 'daily', 'monthly', or 'yearly'.

    Returns:
        float or DataFrame: Temperature-corrected PR as percentage.
    """
    return calculate_temperature_corrected_pr(data, P_STC, gamma, aggregation)