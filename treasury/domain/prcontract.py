from tasks_utils.requests import get_public_api_data


def get_first_stage_tender(task, tender):
    if tender["procurementMethodType"] in ("competitiveDialogueEU.stage2", "competitiveDialogueUA.stage2"):
        tender_id_first_stage = tender["dialogueID"]
        first_stage_tender = get_public_api_data(task, tender_id_first_stage, "tender")
    elif tender["procurementMethodType"] == "closeFrameworkAgreementSelectionUA":
        tender_id_first_stage = tender["agreements"][0]["tender_id"]
        first_stage_tender = get_public_api_data(task, tender_id_first_stage, "tender")
    else:
        # tender initially was in the first stage
        first_stage_tender = tender
    return first_stage_tender
