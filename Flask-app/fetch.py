from flask import Flask
from flask import request
from flask import jsonify

from flask_cors import CORS

from flask_sqlalchemy import SQLAlchemy

import configparser

# Response messages
INVALID_EMPLOYEE = "Invalid employee ID sent in the request."
NO_EMPLOYEE = "Employee not found."
INVALID_SUPERIOR = "Invalid superior ID."
MISSING_DETAILS = "Missing one or more employee details."
INVALID_EMPLOYEE_DATA = "Invalid employee data sent in the request."
INVALID_EMPLOYEE_NAME = "Invalid employee name sent in the request."
EMPLOYEE_ADDED_MSG = "Employee added successfully."
EMPLOYEE_UPDATED_MSG = "Employee updated successfully."
EMPLOYEE_DELETED_MSG = "Employee deleted successfully and the no.of subordinates that had their superior unassigned is"
NO_HIERARCH = "Unable to find hierarch for employee"

# Sensitive info retrieved from an .ini file
config = configparser.ConfigParser()
config.read(
    "C:/Users/Vizard/Programming/python/Hierarchy/Flask-app/static/appConfig.ini"
)

user = config.get("MYSQL_DB", "user")
password = config.get("MYSQL_DB", "password")
host = config.get("MYSQL_DB", "host")
port = config.get("MYSQL_DB", "port")
database = "employees"

# Creating the flask app and connecting to the mysql database
app = Flask(__name__)
cors = CORS(app, origins="*")
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"
app.secret_key = config.get("Flask", "secret_key")

# ORM object
db = SQLAlchemy(app)


# Employees table schema using ORM
class employees(db.Model):
    id = db.Column("employee_id", db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    superior_id = db.Column(db.Integer, db.ForeignKey("employees.employee_id"))

    def __init__(self, name, age, address, superior) -> None:
        self.name = name
        self.age = age
        self.address = address
        self.superior_id = superior


# Creates the table with the current app context
with app.app_context():
    db.create_all()


# Default path displays the employee table
@app.route("/")
def index():
    employees_list = []
    for employee in employees.query.all():
        employee_details = {
            "id": employee.id,
            "name": employee.name,
            "age": employee.age,
            "address": employee.address,
            "superior_id": employee.superior_id,
        }
        employees_list.append(employee_details)

    return jsonify(employees_list)


# Searches for an employee using id or name
@app.route("/search/<string:name>", methods=["GET"])
def search_employee(name):
    if not name:
        return jsonify({"message": INVALID_EMPLOYEE_NAME}), 400

    pattern = f"^{name}"
    employees_matches = []
    matches = employees.query.filter(employees.name.op("regexp")(pattern)).all()

    if not matches:
        return jsonify([]), 200

    for employee in matches:
        employees_matches.append({"id": employee.id, "name": employee.name})

    return jsonify(employees_matches)


@app.route("/get-employee/<int:employee_id>", methods=["GET"])
def get_employee(employee_id):
    if not employee_id:
        return jsonify({"message": INVALID_EMPLOYEE}), 400

    employee = employees.query.filter_by(id=employee_id).first()
    if not employee:
        return jsonify({"message": NO_EMPLOYEE}), 404

    employee_data = {
        "id": employee.id,
        "name": employee.name,
        "age": employee.age,
        "address": employee.address,
        "superior_id": employee.superior_id,
    }

    return jsonify(employee_data)


# Searches for an employee's commandChain using id
@app.route("/command-chain/<int:employee_id>", methods=["GET"])
def get_command_chain(employee_id):
    if not employee_id:
        return jsonify({"message": INVALID_EMPLOYEE}), 400

    employee = employees.query.filter_by(id=employee_id).first()
    if not employee:
        return jsonify({"message": NO_EMPLOYEE}), 404

    command_chain = [
        {"id": employee.id, "name": employee.name, "superior_id": employee.superior_id}
    ]
    seen_employee= set()
    seen_employee.add(employee.id)

    while employee.superior_id:
        employee = employees.query.filter_by(id=employee.superior_id).first()

        if employee.id in seen_employee:
            return jsonify({"message": f"{NO_HIERARCH} {employee_id}."}), 404
        else:
            seen_employee.add(employee.id)

        command_chain.insert(
            0,
            {
                "id": employee.id,
                "name": employee.name,
                "superior_id": employee.superior_id,
            },
        )

    return jsonify(command_chain)


# Searches for an employee's subordinates using id
@app.route("/subordinates/<int:employee_id>", methods=["GET"])
def get_subordinates(employee_id):
    if not employee_id:
        return jsonify({"message": INVALID_EMPLOYEE}), 400

    subordinates = employees.query.filter_by(superior_id=employee_id).all()

    if not subordinates:
        return jsonify([])

    subordinates_list = []
    for subordinate in subordinates:
        subordinates_list.append(
            {
                "id": subordinate.id,
                "name": subordinate.name,
                "superior_id": subordinate.superior_id,
            }
        )

    return jsonify(subordinates_list)


# Used to add new employee details through a form
@app.route("/add", methods=["POST"])
def add_employee():
    employee_data = request.json
    if not employee_data:
        return jsonify({"message": INVALID_EMPLOYEE_DATA}), 400

    name = employee_data["name"]
    age = employee_data["age"]
    address = employee_data["address"]
    if "superior_id" in employee_data and employee_data["superior_id"] > 0:
        superior_id = employee_data["superior_id"]
    else:
        superior_id = None

    if not all([name, age, address]):
        return jsonify({"message": MISSING_DETAILS}), 400

    if superior_id:
        superior_check = employees.query.filter_by(id=superior_id).first()
        if not superior_check:
            return jsonify({"message": INVALID_SUPERIOR}), 400

    employee = employees(name, age, address, superior_id)

    db.session.add(employee)
    db.session.commit()
    return jsonify(EMPLOYEE_ADDED_MSG), 200


# Update employee data
@app.route("/update", methods=["POST"])
def update_employee():
    employee_data = request.get_json()
    if not employee_data:
        return jsonify({"message": INVALID_EMPLOYEE_DATA}), 400

    employee = employees.query.filter_by(id=employee_data["id"]).first()
    if not employee:
        return jsonify({"message": NO_EMPLOYEE}), 404

    for key, value in employee_data.items():
        if key in ["name", "age", "address"] and value is None:
            return jsonify({"message": MISSING_DETAILS})

    if "superior_id" in employee_data and employee_data["superior_id"]:
        superior_check = employees.query.filter_by(
            id=employee_data["superior_id"]
        ).first()

        if not superior_check:
            return jsonify({"message": INVALID_SUPERIOR}), 400

        employee.superior_id = employee_data["superior_id"]
    employee.name = employee_data["name"]
    employee.age = employee_data["age"]
    employee.address = employee_data["address"]

    db.session.commit()
    return jsonify(EMPLOYEE_UPDATED_MSG), 200


# Delete employee
@app.route("/delete/<int:employee_id>", methods=["DELETE"])
def delete_employee(employee_id):
    if not employee_id:
        return jsonify({"message": INVALID_EMPLOYEE}), 400

    employee = employees.query.filter_by(id=employee_id).first()

    if not employee:
        return jsonify({"message": NO_EMPLOYEE}), 404

    subordinates_updated = employees.query.filter_by(superior_id=employee.id).update(
        dict(superior_id=None)
    )

    db.session.delete(employee)
    db.session.commit()
    return jsonify(f"{EMPLOYEE_DELETED_MSG} {subordinates_updated}"), 200


if __name__ == "__main__":
    app.run(debug=True)
