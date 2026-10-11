"""
Employee Management System with HR Analytics
Requirements:
    pip install pymysql pandas matplotlib

Set database credentials with environment variables:
    DB_HOST (optional; defaults to localhost)
    DB_USER (optional; defaults to root)
    DB_PASSWORD (required)
    DB_NAME (optional; defaults to company)
"""

import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import matplotlib.pyplot as plt
import pandas as pd
import pymysql
from pymysql.err import IntegrityError, MySQLError


DB_CONFIG = {
    "host": os.getenv("DB_HOST", ""),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "company"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.Cursor,
    "autocommit": False,
}


CREATE_EMPLOYEE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS employee (
    EmployeeID INT NOT NULL PRIMARY KEY,
    Employee_Name VARCHAR(100) NOT NULL,
    Age TINYINT UNSIGNED NOT NULL,
    Salary DECIMAL(12, 2) NOT NULL,
    Date_of_Joining DATE NOT NULL,
    Post VARCHAR(100) NOT NULL,
    CONSTRAINT chk_employee_age CHECK (Age BETWEEN 16 AND 100),
    CONSTRAINT chk_employee_salary CHECK (Salary >= 0)
)
"""


def connect_db():
    """Create a database connection using environment-based credentials."""
    if not DB_CONFIG["password"]:
        raise RuntimeError(
            "Database password is not set. Set the DB_PASSWORD environment variable."
        )
    return pymysql.connect(**DB_CONFIG)


def ensure_schema(con):
    """Create the employee table if it does not already exist."""
    with con.cursor() as cur:
        cur.execute(CREATE_EMPLOYEE_TABLE_SQL)
    con.commit()


def prompt_text(label, *, max_length=100):
    while True:
        value = input(label).strip()
        if not value:
            print("Input cannot be empty.")
        elif len(value) > max_length:
            print(f"Please enter no more than {max_length} characters.")
        else:
            return value


def prompt_int(label, *, minimum=None, maximum=None):
    while True:
        raw = input(label).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Value must be at least {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be no more than {maximum}.")
            continue
        return value


def prompt_money(label, *, minimum=Decimal("0.00")):
    while True:
        raw = input(label).strip().replace(",", "")
        try:
            value = Decimal(raw).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            print("Enter a valid amount, for example 45000 or 45000.50.")
            continue
        if not value.is_finite():
            print("Enter a finite numeric amount.")
        elif value < minimum:
            print(f"Amount must be at least {minimum}.")
        elif value > Decimal("9999999999.99"):
            print("Amount is too large for the database column.")
        else:
            return value


def prompt_date(label):
    while True:
        raw = input(label).strip()
        try:
            value = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            print("Enter a valid date in YYYY-MM-DD format.")
            continue
        if value > date.today():
            print("Date cannot be in the future.")
            continue
        return value


def employee_exists(cur, empid):
    cur.execute("SELECT 1 FROM employee WHERE EmployeeID = %s", (empid,))
    return cur.fetchone() is not None


def print_records(records):
    if not records:
        print("\nNo matching employee records found.\n")
        return
    headers = [
        "EmployeeID", "Employee_Name", "Age", "Salary",
        "Date_of_Joining", "Post"
    ]
    print()
    print(" | ".join(headers))
    print("-" * 105)
    for row in records:
        print(" | ".join(str(value) for value in row))
    print()


def register_employee(cur, con):
    print("\n--- Employee Registration ---")
    empid = prompt_int("Enter Employee ID: ", minimum=1, maximum=2147483647)
    name = prompt_text("Enter Employee Name: ", max_length=100)
    age = prompt_int("Enter Age (16-100): ", minimum=16, maximum=100)
    salary = prompt_money("Enter Salary: ")
    doj = prompt_date("Enter Date of Joining (YYYY-MM-DD): ")
    post = prompt_text("Enter Post/Job Title: ", max_length=100)

    try:
        cur.execute(
            """
            INSERT INTO employee
                (EmployeeID, Employee_Name, Age, Salary, Date_of_Joining, Post)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (empid, name, age, salary, doj, post),
        )
        con.commit()
        print("\n[Success] Employee registered successfully.\n")
    except IntegrityError:
        con.rollback()
        print("\n[Error] That Employee ID already exists or a database constraint failed.\n")
    except MySQLError as exc:
        con.rollback()
        print(f"\n[Database Error] Registration failed: {exc}\n")


def display_employees(cur):
    cur.execute(
        """
        SELECT EmployeeID, Employee_Name, Age, Salary, Date_of_Joining, Post
        FROM employee ORDER BY EmployeeID
        """
    )
    print_records(cur.fetchall())


SEARCH_FIELDS = {
    "1": ("EmployeeID", "Employee ID"),
    "2": ("Employee_Name", "Employee Name"),
    "3": ("Age", "Age"),
    "4": ("Salary", "Salary"),
    "5": ("Date_of_Joining", "Date of Joining"),
    "6": ("Post", "Post/Job Title"),
}


def search_employee(cur):
    print("\n--- Search Employees ---")
    print("Search by: 1. ID  2. Name  3. Age  4. Salary  5. Joining Date  6. Post")
    choice = input("Choose field (1-6): ").strip()
    if choice not in SEARCH_FIELDS:
        print("Invalid field choice.")
        return

    field, label = SEARCH_FIELDS[choice]
    allowed_columns = {item[0] for item in SEARCH_FIELDS.values()}
    if field not in allowed_columns:
        print("Invalid search field.")
        return

    if field in ("Employee_Name", "Post"):
        term = prompt_text(f"Enter {label} (partial matches allowed): ", max_length=100)
        cur.execute(
            f"SELECT EmployeeID, Employee_Name, Age, Salary, Date_of_Joining, Post "
            f"FROM employee WHERE {field} LIKE %s ORDER BY EmployeeID",
            (f"%{term}%",),
        )
    elif field in ("Age", "Salary"):
        print("1. Equals  2. Greater than  3. Less than  4. Between")
        op = input("Choose comparison (1-4): ").strip()
        if op not in {"1", "2", "3", "4"}:
            print("Invalid comparison choice.")
            return
        if field == "Age":
            first = prompt_int("Enter age: ", minimum=16, maximum=100)
        else:
            first = prompt_money("Enter salary: ")
        if op == "1":
            sql_op = "="
            params = (first,)
        elif op == "2":
            sql_op = ">"
            params = (first,)
        elif op == "3":
            sql_op = "<"
            params = (first,)
        else:
            if field == "Age":
                second = prompt_int("Enter upper age: ", minimum=16, maximum=100)
            else:
                second = prompt_money("Enter upper salary: ")
            low, high = sorted((first, second))
            cur.execute(
                f"SELECT EmployeeID, Employee_Name, Age, Salary, Date_of_Joining, Post "
                f"FROM employee WHERE {field} BETWEEN %s AND %s ORDER BY EmployeeID",
                (low, high),
            )
            print_records(cur.fetchall())
            return
        cur.execute(
            f"SELECT EmployeeID, Employee_Name, Age, Salary, Date_of_Joining, Post "
            f"FROM employee WHERE {field} {sql_op} %s ORDER BY EmployeeID",
            params,
        )
    elif field == "Date_of_Joining":
        print("1. On date  2. Before date  3. After date  4. Between dates")
        op = input("Choose comparison (1-4): ").strip()
        if op not in {"1", "2", "3", "4"}:
            print("Invalid comparison choice.")
            return
        first = prompt_date("Enter date (YYYY-MM-DD): ")
        if op == "4":
            second = prompt_date("Enter end date (YYYY-MM-DD): ")
            start, end = sorted((first, second))
            cur.execute(
                "SELECT EmployeeID, Employee_Name, Age, Salary, Date_of_Joining, Post "
                "FROM employee WHERE Date_of_Joining BETWEEN %s AND %s ORDER BY EmployeeID",
                (start, end),
            )
        else:
            sql_op = {"1": "=", "2": "<", "3": ">"}[op]
            cur.execute(
                f"SELECT EmployeeID, Employee_Name, Age, Salary, Date_of_Joining, Post "
                f"FROM employee WHERE Date_of_Joining {sql_op} %s ORDER BY EmployeeID",
                (first,),
            )
    else:
        empid = prompt_int("Enter Employee ID: ", minimum=1)
        cur.execute(
            "SELECT EmployeeID, Employee_Name, Age, Salary, Date_of_Joining, Post "
            "FROM employee WHERE EmployeeID = %s",
            (empid,),
        )
    print_records(cur.fetchall())


def update_employee(cur, con):
    print("\n--- Update Employee ---")
    empid = prompt_int("Enter ID of the employee to update: ", minimum=1)
    if not employee_exists(cur, empid):
        print("No employee found with that ID.")
        return

    print("1. Employee ID  2. Name  3. Age  4. Salary  5. Joining Date  6. Post")
    choice = input("Choose field to update (1-6): ").strip()

    try:
        if choice == "1":
            new_id = prompt_int("Enter new Employee ID: ", minimum=1, maximum=2147483647)
            cur.execute(
                "UPDATE employee SET EmployeeID = %s WHERE EmployeeID = %s",
                (new_id, empid),
            )
        elif choice == "2":
            value = prompt_text("Enter new name: ", max_length=100)
            cur.execute(
                "UPDATE employee SET Employee_Name = %s WHERE EmployeeID = %s",
                (value, empid),
            )
        elif choice == "3":
            value = prompt_int("Enter new age (16-100): ", minimum=16, maximum=100)
            cur.execute("UPDATE employee SET Age = %s WHERE EmployeeID = %s", (value, empid))
        elif choice == "4":
            print("1. Set salary  2. Increase salary  3. Decrease salary")
            sub = input("Choose salary action (1-3): ").strip()
            if sub == "1":
                value = prompt_money("Enter new salary: ")
                cur.execute("UPDATE employee SET Salary = %s WHERE EmployeeID = %s", (value, empid))
            elif sub in {"2", "3"}:
                value = prompt_money("Enter amount: ")
                operator = "+" if sub == "2" else "-"
                if sub == "3":
                    cur.execute("SELECT Salary FROM employee WHERE EmployeeID = %s", (empid,))
                    current = Decimal(str(cur.fetchone()[0]))
                    if value > current:
                        print("Decrease amount cannot exceed current salary.")
                        return
                cur.execute(
                    f"UPDATE employee SET Salary = Salary {operator} %s WHERE EmployeeID = %s",
                    (value, empid),
                )
            else:
                print("Invalid salary action.")
                return
        elif choice == "5":
            value = prompt_date("Enter new joining date (YYYY-MM-DD): ")
            cur.execute(
                "UPDATE employee SET Date_of_Joining = %s WHERE EmployeeID = %s",
                (value, empid),
            )
        elif choice == "6":
            value = prompt_text("Enter new post: ", max_length=100)
            cur.execute("UPDATE employee SET Post = %s WHERE EmployeeID = %s", (value, empid))
        else:
            print("Invalid update choice.")
            return

        if cur.rowcount:
            con.commit()
            print("\n[Success] Employee record updated.\n")
        else:
            con.rollback()
            print("\n[Notice] No changes were made.\n")
    except IntegrityError:
        con.rollback()
        print("\n[Error] Update failed: duplicate ID or database constraint violation.\n")
    except MySQLError as exc:
        con.rollback()
        print(f"\n[Database Error] Update failed: {exc}\n")


def remove_employee(cur, con):
    print("\n--- Remove Employee ---")
    empid = prompt_int("Enter Employee ID to remove: ", minimum=1)
    if not employee_exists(cur, empid):
        print("No employee found with that ID.")
        return
    confirm = input(f"Delete employee {empid}? Type YES to confirm: ").strip()
    if confirm != "YES":
        print("Deletion cancelled.")
        return
    try:
        cur.execute("DELETE FROM employee WHERE EmployeeID = %s", (empid,))
        con.commit()
        if cur.rowcount:
            print("\n[Success] Employee removed.\n")
        else:
            print("\n[Notice] No record was deleted.\n")
    except MySQLError as exc:
        con.rollback()
        print(f"\n[Database Error] Deletion failed: {exc}\n")


def load_employee_dataframe(cur):
    cur.execute(
        """
        SELECT EmployeeID, Employee_Name, Age, Salary, Date_of_Joining, Post
        FROM employee
        ORDER BY EmployeeID
        """
    )
    rows = cur.fetchall()
    columns = ["EmployeeID", "Employee_Name", "Age", "Salary", "Date_of_Joining", "Post"]
    df = pd.DataFrame(rows, columns=columns)
    if not df.empty:
        df["Date_of_Joining"] = pd.to_datetime(df["Date_of_Joining"], errors="coerce")
        df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce")
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
        today = pd.Timestamp.today().normalize()
        df["Tenure_Years"] = ((today - df["Date_of_Joining"]).dt.days / 365.25).clip(lower=0)
        df["Joining_Month"] = df["Date_of_Joining"].dt.to_period("M").astype(str)
    return df


def run_hr_analytics(cur):
    """Print HR KPIs and draw multiple analytics charts."""
    try:
        df = load_employee_dataframe(cur)
        if df.empty:
            print("\n[Notice] No employee records found. Add employees before running analytics.\n")
            return

        print("\n" + "=" * 54)
        print("             HR ANALYTICS DASHBOARD")
        print("=" * 54)
        print(f"Total employees       : {len(df):,}")
        print(f"Average age           : {df['Age'].mean():.1f} years")
        print(f"Median age            : {df['Age'].median():.1f} years")
        print(f"Average salary        : ₹{df['Salary'].mean():,.2f}")
        print(f"Median salary         : ₹{df['Salary'].median():,.2f}")
        print(f"Minimum salary        : ₹{df['Salary'].min():,.2f}")
        print(f"Maximum salary        : ₹{df['Salary'].max():,.2f}")
        print(f"Average tenure        : {df['Tenure_Years'].mean():.1f} years")
        print(f"Employees under 30    : {(df['Age'] < 30).sum():,}")
        print(f"Employees aged 50+    : {(df['Age'] >= 50).sum():,}")

        salary_by_post = (
            df.groupby("Post", dropna=False)["Salary"]
            .agg(["count", "mean", "median", "min", "max"])
            .sort_values("mean", ascending=False)
        )
        salary_by_post.columns = [
            "Employee Count", "Average Salary", "Median Salary", "Minimum Salary", "Maximum Salary"
        ]
        print("\n--- Workforce by Post ---")
        print(df.groupby("Post").size().sort_values(ascending=False).to_string())
        print("\n--- Salary Statistics by Post ---")
        print(salary_by_post.to_string(float_format=lambda x: f"{x:,.2f}"))

        monthly_hires = (
            df.dropna(subset=["Date_of_Joining"])
            .groupby(df["Date_of_Joining"].dt.to_period("M"))
            .size()
        )
        print("\n--- Hiring Summary ---")
        print(f"First joining date    : {df['Date_of_Joining'].min().date()}")
        print(f"Most recent joining   : {df['Date_of_Joining'].max().date()}")
        print(f"Posts represented     : {df['Post'].nunique()}")

        fig, axes = plt.subplots(2, 2, figsize=(13, 9))

        salary_by_post["Average Salary"].sort_values().plot(
            kind="barh", ax=axes[0, 0], edgecolor="black"
        )
        axes[0, 0].set_title("Average Salary by Post")
        axes[0, 0].set_xlabel("Average Salary (₹)")
        axes[0, 0].grid(axis="x", linestyle="--", alpha=0.4)

        df["Age"].dropna().plot(
            kind="hist", bins=min(10, max(5, int(df["Age"].nunique()))),
            ax=axes[0, 1], edgecolor="black"
        )
        axes[0, 1].set_title("Employee Age Distribution")
        axes[0, 1].set_xlabel("Age")
        axes[0, 1].set_ylabel("Number of Employees")

        df.groupby("Post").size().sort_values().plot(
            kind="barh", ax=axes[1, 0], edgecolor="black"
        )
        axes[1, 0].set_title("Employee Count by Post")
        axes[1, 0].set_xlabel("Number of Employees")
        axes[1, 0].grid(axis="x", linestyle="--", alpha=0.4)

        if not monthly_hires.empty:
            monthly_hires.index = monthly_hires.index.astype(str)
            monthly_hires.plot(kind="line", marker="o", ax=axes[1, 1])
            axes[1, 1].tick_params(axis="x", rotation=45)
        axes[1, 1].set_title("Hiring Trend by Month")
        axes[1, 1].set_xlabel("Joining Month")
        axes[1, 1].set_ylabel("Employees Joined")
        axes[1, 1].grid(axis="y", linestyle="--", alpha=0.4)

        fig.suptitle("HR Analytics & Workforce Insights", fontsize=15)
        fig.tight_layout()
        plt.show()

        save = input("Save analytics charts as hr_analytics_dashboard.png? (y/n): ").strip().lower()
        if save == "y":
            fig.savefig("hr_analytics_dashboard.png", dpi=160, bbox_inches="tight")
            print("Chart saved as hr_analytics_dashboard.png")
        plt.close(fig)

        export = input("Export employee data and post-level salary statistics to CSV? (y/n): ").strip().lower()
        if export == "y":
            df.to_csv("employee_analytics.csv", index=False)
            salary_by_post.to_csv("salary_by_post.csv")
            print("Saved employee_analytics.csv and salary_by_post.csv")

    except (MySQLError, ValueError, KeyError) as exc:
        print(f"\n[Analytics Error] Could not complete analytics: {exc}\n")


def main():
    con = None
    cur = None
    try:
        con = connect_db()
        ensure_schema(con)
        cur = con.cursor()
        print("\nConnected to MySQL database successfully.")
        print("Employee table is ready.")
        while True:
            print(
                "\n========== EMPLOYEE MANAGEMENT SYSTEM ==========\n"
                "1. Employee Registration\n"
                "2. Display All Employees\n"
                "3. Search Employee\n"
                "4. Update Employee\n"
                "5. Remove Employee\n"
                "6. HR Analytics Dashboard\n"
                "7. Exit\n"
                "================================================"
            )
            choice = input("Enter your choice (1-7): ").strip()
            try:
                if choice == "1":
                    register_employee(cur, con)
                elif choice == "2":
                    display_employees(cur)
                elif choice == "3":
                    search_employee(cur)
                elif choice == "4":
                    update_employee(cur, con)
                elif choice == "5":
                    remove_employee(cur, con)
                elif choice == "6":
                    run_hr_analytics(cur)
                elif choice == "7":
                    print("Exiting application. Goodbye!")
                    break
                else:
                    print("Please enter a number from 1 to 7.")
            except MySQLError as exc:
                con.rollback()
                print(f"\n[Database Error] Operation failed: {exc}\n")
    except (MySQLError, RuntimeError) as exc:
        print(f"\n[Startup Error] {exc}")
        print("Check that MySQL is running, the database exists, and credentials are correct.")
    finally:
        if cur is not None:
            cur.close()
        if con is not None:
            con.close()


if __name__ == "__main__":
    main()
