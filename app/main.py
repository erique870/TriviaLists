from fastapi import FastAPI

app = FastAPI(
    title="Trivialists API",
    description="API para gestão de cardápios e pedidos de refeições.",
    version="0.1.0",
)


@app.get("/", tags=["TesteDaSilva"])
def health_check() -> dict[str, str]:
    return {"Teste": "ok"}
