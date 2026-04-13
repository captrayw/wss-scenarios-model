import io
import csv
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from model.inputs import ModelInputs
from model.engine import calculate

app = FastAPI(title="WSS Scenarios Model API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/defaults")
def get_defaults():
    return ModelInputs().model_dump()


@app.post("/api/calculate")
def run_calculation(inputs: ModelInputs):
    return calculate(inputs)


@app.post("/api/export/csv")
def export_csv(inputs: ModelInputs):
    result = calculate(inputs)

    years = result['years']
    total_hh = result['total_hh']
    ws = result['water_supply']
    san = result['sanitation']

    columns = [
        'Year', 'Total_HH',
        'WS_BAU_Serv1', 'WS_Target_Serv1', 'WS_Service_Gap',
        'WS_Investment_Need', 'WS_BAU_Investment', 'WS_Financing_Gap',
        'SAN_BAU_Serv1', 'SAN_Target_Serv1', 'SAN_Service_Gap',
        'SAN_Investment_Need', 'SAN_BAU_Investment', 'SAN_Financing_Gap',
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)

    for i, year in enumerate(years):
        writer.writerow([
            year,
            total_hh[i],
            ws['bau_hh_serv'][0][i],
            ws['target_hh_serv'][0][i],
            ws['service_gap'][i],
            ws['investment_need'][i],
            ws['bau_investment'][i],
            ws['financing_gap'][i],
            san['bau_hh_serv'][0][i],
            san['target_hh_serv'][0][i],
            san['service_gap'][i],
            san['investment_need'][i],
            san['bau_investment'][i],
            san['financing_gap'][i],
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="wss_results.csv"'},
    )


@app.post("/api/export/pptx")
def export_pptx(inputs: ModelInputs):
    from export_pptx import create_pptx
    result = calculate(inputs)
    output = create_pptx(result, inputs.model_dump())
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        headers={'Content-Disposition': 'attachment; filename="wss_scenarios.pptx"'},
    )


@app.post("/api/export/xlsx")
def export_xlsx(inputs: ModelInputs):
    from openpyxl import Workbook
    result = calculate(inputs)
    wb = Workbook()

    for sector_key, sector_name in [('water_supply', 'Water Supply'), ('sanitation', 'Sanitation')]:
        ws = wb.create_sheet(title=sector_name)
        sec = result[sector_key]
        headers = ['Year', 'Total HH', 'Target Serv1', 'BAU Serv1', 'Service Gap',
                   'Investment Need', 'BAU Investment', 'Financing Gap']
        ws.append(headers)
        for i, year in enumerate(result['years']):
            ws.append([
                year, result['total_hh'][i],
                sec['target_hh_serv'][0][i], sec['bau_hh_serv'][0][i], sec['service_gap'][i],
                sec['investment_need'][i], sec['bau_investment'][i], sec['financing_gap'][i],
            ])

    if 'Sheet' in wb.sheetnames:
        del wb['Sheet']

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="wss_results.xlsx"'},
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve frontend static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))
