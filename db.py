from typing import Any
from dotenv import load_dotenv
from get_data import preprocess_data

load_dotenv()

class DatabaseConnection:
    def __init__(self):
        self.conn = None
        self._connect()
    
    def _connect(self):
        import duckdb
        
        df = preprocess_data()
        self.conn = duckdb.connect("data.duckdb") 
        self.conn.execute("CREATE OR REPLACE TABLE solar AS SELECT * FROM df")

    def is_closed(self) -> bool:
        return True
    
    def reconnect(self):
        if self.is_closed():
            print(f"⚠️  Connection closed. Reconnecting to database")
            self._connect()
    
    def execute(self, query: str) -> Any:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string
            
        Returns:
            Query results with a fetchdf() method for pandas DataFrame
        """
        # Check and reconnect if necessary
        if self.is_closed():
            self.reconnect()
        
        return self.conn.execute(query)
    
    def close(self):
        if self.conn:
            self.conn.close()
            print(f"✓ Closed database connection")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def get_connection() -> DatabaseConnection:
    return DatabaseConnection()