import psycopg2
from command.sql.base import BaseSQLCommand


class PostgresSQLCommand(BaseSQLCommand):
    """
    PostgreSQL SQL Command 实现
    """

    def run(self, sql: str, context: dict):
        """
        执行 SQL 并返回统一结果结构
        """
        conn = psycopg2.connect(
            host=context["pg_host"],
            port=context.get("pg_port", 5432),
            user=context["pg_user"],
            password=context["pg_password"],
            dbname=context["pg_db"],
        )

        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql)

                    # SELECT 才有结果
                    if cur.description:
                        rows = cur.fetchall()
                        stdout = "\n".join(str(r) for r in rows)
                    else:
                        stdout = ""

            return {
                "stdout": stdout,
                "stderr": "",
                "rc": 0,
            }

        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "rc": 1,
            }

        finally:
            conn.close()
