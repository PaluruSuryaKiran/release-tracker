# release-tracker
 
`release-tracker` is an HTTP REST API service for DevOps and software engineers to record packages and their releases. It is shipped as a snap and available for all Linux machines with snapd. 

**The snap is a development build on the `edge` channel and is not meant for production use.**
 
## Quick start
 
1. Check that your machine has snapd:
   ```
   snap --version
   ```
   
   The output is similar to:
   
   ```
   snap    2.63.1
   snapd   2.63.1
   series  16
   ubuntu  24.04
   ```
   
   Ubuntu has snapd already. On other distributions, follow the [snapd installation guide](https://snapcraft.io/docs/installing-snapd).

   Then install the release-tracker snap:
   
   ```
   sudo snap install release-tracker-surya --edge
   ```
 
2. Install PostgreSQL and create a database for the service:
   ```
   sudo apt install -y postgresql
   sudo -u postgres psql -c "CREATE USER <user> WITH PASSWORD '<password>';"
   sudo -u postgres psql -c "CREATE DATABASE <database> OWNER <user>;"
   ```
   
   Replace `<user>` and `<password>` with a username and password of your choice, and `<database>` with a name for the database, such as `releases`.

   If you already have a PostgreSQL server, skip this step and use its details in the next one.
   
3. Point the service at the database:
   ```
   sudo snap set release-tracker-surya database-url="postgresql+psycopg://<user>:<password>@<host>/<database>"
   ```
   
   Use the values from the previous step. For a database on the same machine, `<host>` is `localhost`.

   Setting the URL starts the service. Check that it is running:
   
   ```
   snap services release-tracker-surya
   ```
   
   The service should show as `enabled` and `active`:
   
   ```
   Service                       Startup  Current  Notes
   release-tracker-surya.server  enabled  active   -
   ```
 
4. Create a package:
   ```
   curl -X POST http://localhost:8000/packages \
   -H "Content-Type: application/json" \
   -d '{"name": "hello-world", "description": "Test package"}'
   ```
   
   The output is similar to:
   
   ```
   {"name":"hello-world","description":"Test package","created_at":"2026-11-20T12:20:09.512345Z","latest_version":null}
   ```
   
   The package has no releases yet, so `latest_version` is `null`.
   
5. Add two releases, first `1.9.0` and then `1.10.0`:
   ```
   curl -X POST http://localhost:8000/packages/hello-world/releases \
   -H "Content-Type: application/json" \
   -d '{"version": "1.9.0"}'
   ```
   
   ```
   curl -X POST http://localhost:8000/packages/hello-world/releases \
   -H "Content-Type: application/json" \
   -d '{"version": "1.10.0"}'
   ```
   
   Each request returns the release it created, similar to:
   
   ```
   {"version":"1.10.0","released_at":"2026-11-20T12:20:31.204816Z"}
   ```
 
6. Get the package again:
   ```
   curl http://localhost:8000/packages/hello-world
   ```
   
   The output is similar to:
   
   ```
   {"name":"hello-world","description":"Test package","created_at":"2026-11-20T12:20:09.512345Z","latest_version":"1.10.0"}
   ```
   
   The latest version is `1.10.0`, not `1.9.0`.
 
That's it, you have a running service with one package and two releases. See the API section below for every endpoint, or open the interactive docs at `http://localhost:8000/docs` while the service is running.
 
## API
 
All requests and responses are JSON. Errors come back with a `detail` field explaining what went wrong.
 
**`GET /health`**
 
Returns `{"status":"ok"}` when the service is running.
 
**`POST /packages`**
 
Creates a package. The body takes:
 
- `name` (required): 2 to 100 characters, lowercase letters, digits and hyphens only, starting with a letter.
- `description` (optional): up to 500 characters.

Returns 201 with the package. Returns 409 if the name is already taken, and 422 if the body is invalid or has extra fields.
 
**`GET /packages/<name>`**
 
Returns the package with its `name`, `description`, `created_at` and `latest_version`. `latest_version` is `null` when the package has no releases. Returns 404 if the package does not exist. Names are case-sensitive, so `Hello-World` will not find `hello-world`.
 
**`POST /packages/<name>/releases`**
 
Adds a release. The body takes:
 
- `version` (required): `MAJOR.MINOR.PATCH`, such as `1.4.2`. No leading zeros, no `v` prefix, and at most 15 characters.

Returns 201 with the `version` and `released_at`. Returns 404 if the package does not exist, 409 if that version already exists for the package, and 422 if the version is invalid.
 
## Configuration
 
The snap has two settings:
 
- `database-url` (required): the PostgreSQL URL, in the form `postgresql+psycopg://<user>:<password>@<host>/<database>`.
- `port` (optional): the port the service listens on. The default is `8000`.

Change a setting with:
 
```
sudo snap set release-tracker-surya <key>=<value>
```
 
The service restarts on its own when a setting changes. A database URL that does not start with `postgresql+psycopg://`, or a port that is not a number, is rejected straight away.
 
## Design notes
 
**Versions are sorted as numbers, not text.** Each release stores its major, minor and patch numbers as separate integers next to the version string. Sorted as text, `1.10.0` would come before `1.9.0`. The latest version is worked out by the database, so the service never has to load every release into memory to find it.
 
**The database enforces uniqueness.** Package names, and versions within a package, are protected by unique constraints. Checking for a duplicate in code first would leave a gap where two requests at the same moment both pass the check. Instead, the service just tries the insert and turns a constraint error into a 409.
 
**Packages and releases are separate.** A package is created once and releases are added to it over time. This keeps each request to one job, and a 409 always means one thing.
 
**The snap is strictly confined.** It can only open its port and connect to the network. Settings come from `snap set`, and a small launch script passes them to the app as environment variables, so the app code is the same inside and outside the snap. The service stays off after installing until a valid database URL is set.
 
**Repository layout.** This repository is the release tracker as a whole. `services/package-service` is its first part, the Python service that manages packages and releases.
 
## Limitations
 
- There is no authentication, so anyone who can reach the port can create packages and releases.
- Tables are created at startup and never altered, so schema changes would require migration tools.
- There is no endpoint to list packages or a package's releases yet.

## Contributing
 
To run the service from source, run the tests or build the snap yourself, see [CONTRIBUTING.md](CONTRIBUTING.md).
 
## License
 
Apache-2.0. See [LICENSE](LICENSE).