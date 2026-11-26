from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version as package_version
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request, Response, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from package_service.db import Base, engine, get_session
from package_service.models import Package, Release
from package_service.openapi import (
    DESCRIPTION,
    INVALID,
    TAGS,
    add_problem_schemas,
    operation_id_from_name,
    problem,
)
from package_service.problems import ProblemError, register_problem_handlers
from package_service.schemas import PackageCreate, PackageOut, ReleaseCreate, ReleaseOut
from package_service.versions import parse_version

SessionDep = Annotated[Session, Depends(get_session)]

VERSION_ORDER = (Release.major.desc(), Release.minor.desc(), Release.patch.desc())


def service_version() -> str:
    """The version from pyproject.toml, as installed by pip."""
    try:
        return package_version("package-service")
    except PackageNotFoundError:
        return "0.0.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="release-tracker",
    version=service_version(),
    description=DESCRIPTION,
    license_info={"name": "Apache 2.0", "identifier": "Apache-2.0"},
    openapi_tags=TAGS,
    generate_unique_id_function=operation_id_from_name,
    lifespan=lifespan,
)
v1 = APIRouter(prefix="/v1")
register_problem_handlers(app)
add_problem_schemas(app)


def latest_version_select(package_id):
    return (
        select(Release.version)
        .where(Release.package_id == package_id)
        .order_by(*VERSION_ORDER)
        .limit(1)
    )


def latest_version_of(session: Session, package_id: int) -> str | None:
    return session.scalar(latest_version_select(package_id))


def get_package_or_404(session: Session, name: str) -> Package:
    package = session.scalar(select(Package).where(Package.name == name))
    if package is None:
        raise ProblemError(
            404, "package-not-found", "Package not found",
            f"There is no package named {name!r}.",
        )
    return package


@app.get(
    "/livez",
    tags=["health"],
    summary="Check that the service is running"
)
@app.get("/health", include_in_schema=False)
def health_check():
    """Returns `{"status": "ok"}` while the process is up."""
    return {"status": "ok"}

@app.get(
    "/readyz",
    tags=["health"],
    summary="Check that the service is ready to serve requests",
)
def readiness_check(session: SessionDep):
    """Returns `{"status": "ok"}` if the database is reachable."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise ProblemError(
            503, "not-ready", "Service is not ready",
            f"The database is not reachable",
        )
    return {"status": "ready"}


@v1.post(
    "/packages",
    response_model=PackageOut,
    status_code=status.HTTP_201_CREATED,
    tags=["packages"],
    summary="Create a package",
    responses={409: problem("A package with this name already exists."), **INVALID},
)
def create_package(
    body: PackageCreate, session: SessionDep, request: Request, response: Response
):
    """Registers a new package. The `Location` header points to the new package."""
    package = Package(name=body.name, description=body.description)
    session.add(package)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ProblemError(
            409, "package-exists", "Package already exists",
            f"A package named {body.name!r} already exists.",
        )
    response.headers["Location"] = request.app.url_path_for(
        "get_package", name=package.name
    )
    return package


@v1.get(
    "/packages/{name}",
    response_model=PackageOut,
    tags=["packages"],
    summary="Get a package",
    responses={404: problem("There is no package with this name.")},
)
def get_package(name: str, session: SessionDep):
    """Returns the package and its latest version, or `null` if it has no releases."""
    package = get_package_or_404(session, name)
    return PackageOut(
        name=package.name,
        description=package.description,
        created_at=package.created_at,
        latest_version=latest_version_of(session, package.id),
    )


@v1.post(
    "/packages/{name}/releases",
    response_model=ReleaseOut,
    status_code=status.HTTP_201_CREATED,
    tags=["releases"],
    summary="Add a release",
    responses={
        404: problem("There is no package with this name."),
        409: problem("The package already has this version."),
        **INVALID,
    },
)
def create_release(
    name: str,
    body: ReleaseCreate,
    session: SessionDep,
    request: Request,
    response: Response,
):
    """Adds a `MAJOR.MINOR.PATCH` release. The `Location` header points to it."""
    package = get_package_or_404(session, name)
    v = parse_version(body.version)
    release = Release(
        package_id=package.id,
        version=body.version,
        major=v.major,
        minor=v.minor,
        patch=v.patch,
    )
    session.add(release)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ProblemError(
            409, "release-exists", "Release already exists",
            f"Package {name!r} already has a release {body.version!r}.",
        )
    response.headers["Location"] = request.app.url_path_for(
        "get_release", name=name, version=release.version
    )
    return release


@v1.get(
    "/packages/{name}/releases/{version}",
    response_model=ReleaseOut,
    tags=["releases"],
    summary="Get a release",
    responses={404: problem("There is no such package, or it has no such release.")},
)
def get_release(name: str, version: str, session: SessionDep):
    """Returns one release of a package."""
    package = get_package_or_404(session, name)
    release = session.scalar(
        select(Release).where(
            Release.package_id == package.id, Release.version == version
        )
    )
    if release is None:
        raise ProblemError(
            404, "release-not-found", "Release not found",
            f"Package {name!r} has no release {version!r}.",
        )
    return release


app.include_router(v1)