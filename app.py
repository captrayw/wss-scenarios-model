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
