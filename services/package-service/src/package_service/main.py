from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from package_service.db import Base, engine, get_session
from package_service.models import Package, Release
from package_service.problems import ProblemError, register_problem_handlers
from package_service.schemas import PackageCreate, PackageOut, ReleaseCreate, ReleaseOut
from package_service.versions import parse_version

SessionDep = Annotated[Session, Depends(get_session)]

VERSION_ORDER = (Release.major.desc(), Release.minor.desc(), Release.patch.desc())


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Package Registry", lifespan=lifespan)
v1 = APIRouter(prefix="/v1")
register_problem_handlers(app)


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


@app.get("/health")
def health_check():
    return {"status": "ok"}


@v1.post("/packages", response_model=PackageOut, status_code=status.HTTP_201_CREATED)
def create_package(body: PackageCreate, session: SessionDep, request: Request, response: Response):
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
    response.headers["Location"] = request.app.url_path_for("get_package", name=package.name)
    return package


@v1.get("/packages/{name}", response_model=PackageOut)
def get_package(name: str, session: SessionDep):
    package = get_package_or_404(session, name)
    return PackageOut(
        name=package.name,
        description=package.description,
        created_at=package.created_at,
        latest_version=latest_version_of(session, package.id),
    )


@v1.post("/packages/{name}/releases", response_model=ReleaseOut, status_code=status.HTTP_201_CREATED)
def create_release(name: str, body: ReleaseCreate, session: SessionDep, request: Request, response: Response):
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
    response.headers["Location"] = request.app.url_path_for("get_release", name=name, version=release.version)
    return release


@v1.get("/packages/{name}/releases/{version}", response_model=ReleaseOut)
def get_release(name: str, version: str, session: SessionDep):
    package = get_package_or_404(session, name)
    release = session.scalar(
        select(Release).where(
            Release.package_id == package.id,
            Release.version == version,
        )
    )
    if release is None:
        raise ProblemError(
            404, "release-not-found", "Release not found",
            f"Package {name!r} has no release {version!r}.",
        )
    return release


app.include_router(v1)