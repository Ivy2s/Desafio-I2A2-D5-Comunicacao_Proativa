import uvicorn

from src.main import app


def main() -> None:
    """Inicializa a API e serve o frontend buildado em http://127.0.0.1:8000."""
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
