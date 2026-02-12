"""Vendor data models for the vendor risk module.

Defines immutable Pydantic models for vendor certifications, compliance
records, and full vendor profiles used across the risk assessment pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VendorCertification(BaseModel):
    """An immutable record of a single vendor certification."""

    model_config = ConfigDict(frozen=True)

    cert_id: str = Field(
        ...,
        description="Unique identifier for this certification.",
    )
    name: str = Field(
        ...,
        description="Human-readable certification name.",
    )
    issuing_body: str = Field(
        ...,
        description="Organisation that issued the certification.",
    )
    issue_date: datetime = Field(
        ...,
        description="Date the certification was issued.",
    )
    expiry_date: datetime = Field(
        ...,
        description="Date the certification expires.",
    )
    is_valid: bool = Field(
        default=True,
        description="Whether the certification is currently valid (not expired).",
    )

    @field_validator("is_valid", mode="before")
    @classmethod
    def _default_validity(cls, v: bool | None, info: object) -> bool:
        """Accept an explicit value or fall back to expiry-based check."""
        if v is not None:
            return v
        expiry = info.data.get("expiry_date")  # type: ignore[union-attr]
        if expiry is None:
            return False
        return expiry > datetime.now(timezone.utc)


class ComplianceRecord(BaseModel):
    """An immutable record of a single compliance check result."""

    model_config = ConfigDict(frozen=True)

    record_id: str = Field(
        ...,
        description="Unique identifier for this compliance record.",
    )
    check_date: datetime = Field(
        ...,
        description="UTC date the compliance check was performed.",
    )
    passed: bool = Field(
        ...,
        description="Whether the compliance check was passed.",
    )
    category: str = Field(
        ...,
        description="Compliance category (e.g. 'SAFETY', 'ENVIRONMENTAL').",
    )
    details: str = Field(
        ...,
        description="Human-readable description of the check outcome.",
    )


class VendorProfile(BaseModel):
    """Complete immutable profile for a single vendor."""

    model_config = ConfigDict(frozen=True)

    vendor_id: str = Field(
        ...,
        description="Unique identifier for this vendor.",
    )
    company_name: str = Field(
        ...,
        description="Legal company name of the vendor.",
    )
    industry: str = Field(
        ...,
        description="Industry classification of the vendor.",
    )
    certifications: list[VendorCertification] = Field(
        default_factory=list,
        description="List of certifications held by the vendor.",
    )
    compliance_history: list[ComplianceRecord] = Field(
        default_factory=list,
        description="Historical compliance check records.",
    )
    contact_email: str = Field(
        ...,
        description="Primary contact email for the vendor.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the profile was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the profile was last updated.",
    )
