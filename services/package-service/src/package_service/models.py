from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from package_service.db import Base


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    releases: Mapped[list["Release"]] = relationship(back_populates="package")


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (UniqueConstraint("package_id", "version", name="uq_release_package_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"))
    version: Mapped[str] = mapped_column(String(10))
    major: Mapped[int]
    minor: Mapped[int]
    patch: Mapped[int]
    released_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    package: Mapped["Package"] = relationship(back_populates="releases")