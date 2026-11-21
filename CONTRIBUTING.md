# Contributing to release-tracker
 
`release-tracker` is an HTTP REST API service for DevOps and software engineers to record packages and their releases. It is shipped as a snap and available for all Linux machines with snapd. 

This guide covers running release-tracker from source, running the tests and building the snap yourself.

## What you need

- Python 3.10 or later.
- A PostgreSQL server with two databases: one for the service and a separate one for the tests.

## Run from source

1. Clone the repository and go to the service directory:
   ```
   git clone https://github.com/PaluruSuryaKiran/release-tracker.git
   cd release-tracker/services/package-service
   ```

2. Create a virtual environment and install the service with its development dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```

   Then fill in the two database URLs in `.env`:

   - `DATABASE_URL` is the database the service uses.
   - `TEST_DATABASE_URL` is the database the tests use.

   Both take the form `postgresql+psycopg://<user>:<password>@<host>/<database>`. `.env` is ignored by Git, so your credentials stay on your machine.

4. Start the service:
   ```
   uvicorn package_service.main:app --reload
   ```

   The service listens on `http://localhost:8000`, and `--reload` restarts it whenever you edit the code.

   If port 8000 is already in use, for example by the installed snap, pick another port with `--port`:

   ```
   uvicorn package_service.main:app --reload --port <port>
   ```

   Replace `<port>` with a free port, such as `8001`. The service then listens on `http://localhost:<port>`.

## Run the tests

The tests run against a real PostgreSQL database.

`TEST_DATABASE_URL` must point to a different database from `DATABASE_URL`, because the tests drop every table when they finish. The tests refuse to start if the two are the same.

From `services/package-service`, with the virtual environment active:

```
pytest -v
```

## Build the snap

You need snapcraft, and LXD, which snapcraft uses to build inside a clean container:

```
sudo snap install snapcraft --classic
sudo snap install lxd
sudo lxd init --auto
sudo usermod -aG lxd $USER
newgrp lxd
```

From `services/package-service`, build the snap and install it from the local file:

```
snapcraft
sudo snap install ./release-tracker-surya_*.snap --dangerous
```

`--dangerous` is needed because a snap you build yourself is not signed by the Snap Store.

## Before you commit

Run the tests and make sure they all pass. Each commit should do one thing and leave the tests green.
