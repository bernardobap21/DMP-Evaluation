from fastapi import FastAPI, UploadFile, File, Query
from Evaluator.evaluator import (
    load_dmp,
    evaluate_dmp_against_fip,
    summarize_results,
    save_compliance_table,
)
from Evaluator.goals_checks import run_goals_scoring
from Evaluator.validation_rules import validate_metadata_intentions
# from Evaluator.planned_fairness import check_planned_fairness (need to check this)
from FIP_Mapping.mapping import load_mapping
from FIP_Mapping.utils import transform_mapping
import tempfile
import os


FIP_DIRECTORY = "FIP_Mapping"
FIP_OPTIONS = [f for f in os.listdir(FIP_DIRECTORY) if f.endswith(".json")]

def build_compliance_json(results):
    table = []
    for r in results:
        allowed_values = r["allowed_values"]
        if isinstance(allowed_values, list):
            allowed_str = ", ".join(allowed_values)
        else:
            allowed_str = allowed_values

        if allowed_values == "":
            compliant = "No choice made by community"
        else:
            compliant = "Yes" if r["compliance_status"] == "Compliant" else "No"

        table.append({
            "FIP Question": r["FIP_question"],
            "DCS Field": r["maDMP_field"],
            "maDMP Value": r["field_value"],
            "Accepted Values": allowed_str,
            "Compliant": compliant,
        })
    return table


app = FastAPI()


@app.get("/")
def read_root():
    return {"Welcome": "Your DMP Evaluation API is running!"}


@app.post("/evaluate/")
async def evaluate(
    maDMP_file: UploadFile = File(...),
    fip_mapping_file: str = Query(..., enum=FIP_OPTIONS),
):

    # Validate uploaded DMP file
    if not maDMP_file.filename.endswith(".json"):
        return {
            "error": f"Invalid file type: {maDMP_file.filename}. Only .json files are allowed."
        }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        dmp_path = os.path.join(tmpdir, maDMP_file.filename)
        #mapping_path = os.path.join(tmpdir, fip_mapping_file.filename)

        with open(dmp_path, "wb") as buffer:
            buffer.write(await maDMP_file.read())

        mapping_path = os.path.join(FIP_DIRECTORY, fip_mapping_file)

        # Load DMP and mapping
        dmp = load_dmp(dmp_path)
        mapping_raw = load_mapping(mapping_path)
        mapping = transform_mapping(mapping_raw)

        # Evaluate
        results = evaluate_dmp_against_fip(dmp, mapping)
        present, compliant, total = summarize_results(results)

        # Compliance table 
        compliance_path = os.path.join(tmpdir, "compliance_table.csv")
        save_compliance_table(results, compliance_path)
        compliance_table = build_compliance_json(results)
        # with open(compliance_path, "r", encoding="utf-8") as cfile:
          #  compliance_table = cfile.read()

        # Other results
        goals_results = run_goals_scoring(dmp)
        metadata_validation = validate_metadata_intentions(dmp)
        #planned_fairness = check_planned_fairness(dmp)

    # Return results as JSON
    return {
        "summary": f"{present}/{total} fields present, {compliant}/{total} compliant.",
        "goals_checks": goals_results,
        "metadata_validation": metadata_validation,
        "compliance_table": compliance_table,
        # "Mapping_to_FIP_Results": results,
        #"planned_fairness": planned_fairness,
    }
