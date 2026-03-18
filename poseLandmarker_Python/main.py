import uvicorn

from config.config import HOST, PORT


def main() -> None:
    uvicorn.run(
        app="app:app",
        host=HOST,
        port=PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()
