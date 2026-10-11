CREATE DATABASE IF NOT EXISTS company;
USE company;

CREATE TABLE IF NOT EXISTS employee (
    EmployeeID INT NOT NULL PRIMARY KEY,
    Employee_Name VARCHAR(100) NOT NULL,
    Age TINYINT UNSIGNED NOT NULL,
    Salary DECIMAL(12, 2) NOT NULL,
    Date_of_Joining DATE NOT NULL,
    Post VARCHAR(100) NOT NULL,
    CONSTRAINT chk_employee_age CHECK (Age BETWEEN 16 AND 100),
    CONSTRAINT chk_employee_salary CHECK (Salary >= 0)
);
