from datetime import datetime
from typing import Optional, List
import logging

from beanie import PydanticObjectId

from app.models.institution import (
    Institution,
    Subscription,
    Branding,
    InstitutionSettings,
    Address,
    ContactInfo,
    InstitutionStatus,
    SubscriptionPlan,
)
from app.models.user import User, UserRole, UserStatus
from app.core.security import get_password_hash
from app.core.exceptions import (
    NotFoundError,
    AlreadyExistsError,
    BadRequestError,
)
from .schemas import (
    InstitutionCreateRequest,
    InstitutionUpdateRequest,
    InstitutionResponse,
    InstitutionListResponse,
    InstitutionStatsResponse,
    ContactInfoResponse,
    AddressResponse,
    SubscriptionResponse,
    InstitutionSettingsResponse,
    BrandingResponse,
)

logger = logging.getLogger(__name__)


class InstitutionService:
    """Institution management service (Super Admin only)."""

    @staticmethod
    def _to_response(institution: Institution) -> InstitutionResponse:
        """Convert institution to response."""
        branding = None
        if institution.settings.branding:
            branding = BrandingResponse(
                logo=institution.settings.branding.logo,
                primary_color=institution.settings.branding.primary_color,
                secondary_color=institution.settings.branding.secondary_color,
            )

        address = None
        if institution.contact.address:
            address = AddressResponse(
                street=institution.contact.address.street,
                city=institution.contact.address.city,
                state=institution.contact.address.state,
                country=institution.contact.address.country,
                zip_code=institution.contact.address.zip_code,
            )

        return InstitutionResponse(
            id=str(institution.id),
            name=institution.name,
            slug=institution.slug,
            code=institution.code,
            type=institution.type,
            contact=ContactInfoResponse(
                email=institution.contact.email,
                phone=institution.contact.phone,
                address=address,
            ),
            subscription=SubscriptionResponse(
                plan=institution.subscription.plan,
                start_date=institution.subscription.start_date,
                end_date=institution.subscription.end_date,
                max_users=institution.subscription.max_users,
                max_sheets_per_month=institution.subscription.max_sheets_per_month,
                features=institution.subscription.features,
            ),
            settings=InstitutionSettingsResponse(
                timezone=institution.settings.timezone,
                date_format=institution.settings.date_format,
                default_language=institution.settings.default_language,
                branding=branding,
                passing_percentage=institution.settings.passing_percentage,
                negative_marking=institution.settings.negative_marking,
                negative_mark_value=institution.settings.negative_mark_value,
            ),
            status=institution.status,
            created_at=institution.created_at,
            updated_at=institution.updated_at,
        )

    @staticmethod
    async def get_by_id(institution_id: str) -> Institution:
        """Get institution by ID."""
        institution = await Institution.get(PydanticObjectId(institution_id))
        if not institution:
            raise NotFoundError("Institution", institution_id)
        return institution

    @staticmethod
    async def get_by_code(code: str) -> Institution:
        """Get institution by code."""
        institution = await Institution.find_one(Institution.code == code.upper())
        if not institution:
            raise NotFoundError("Institution", code)
        return institution

    @staticmethod
    async def list_institutions(
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        type: Optional[str] = None,
    ) -> InstitutionListResponse:
        """List all institutions with pagination."""

        # Build query
        query = {}

        if status:
            query["status"] = status

        if type:
            query["type"] = type

        # Build pipeline
        pipeline = [{"$match": query}]

        # Search filter
        if search:
            pipeline.append({
                "$match": {
                    "$or": [
                        {"name": {"$regex": search, "$options": "i"}},
                        {"code": {"$regex": search, "$options": "i"}},
                        {"slug": {"$regex": search, "$options": "i"}},
                    ]
                }
            })

        # Get total count
        count_pipeline = pipeline + [{"$count": "total"}]
        count_result = await Institution.aggregate(count_pipeline).to_list()
        total = count_result[0]["total"] if count_result else 0

        # Pagination
        skip = (page - 1) * page_size
        pipeline.extend([
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": page_size}
        ])

        # Execute
        institutions_data = await Institution.aggregate(pipeline).to_list()

        # Fetch full documents
        items = []
        for inst_data in institutions_data:
            inst = await Institution.get(inst_data["_id"])
            if inst:
                items.append(InstitutionService._to_response(inst))

        total_pages = (total + page_size - 1) // page_size

        return InstitutionListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    async def create(
        request: InstitutionCreateRequest,
        created_by: User
    ) -> Institution:
        """Create new institution."""

        # Check slug uniqueness
        existing_slug = await Institution.find_one(Institution.slug == request.slug)
        if existing_slug:
            raise AlreadyExistsError("Institution", "slug", request.slug)

        # Check code uniqueness
        existing_code = await Institution.find_one(Institution.code == request.code.upper())
        if existing_code:
            raise AlreadyExistsError("Institution", "code", request.code)

        # Build address
        address = None
        if request.contact.address:
            address = Address(
                street=request.contact.address.street,
                city=request.contact.address.city,
                state=request.contact.address.state,
                country=request.contact.address.country,
                zip_code=request.contact.address.zip_code,
            )

        # Build contact
        contact = ContactInfo(
            email=request.contact.email,
            phone=request.contact.phone,
            address=address or Address(),
        )

        # Build subscription
        subscription = Subscription()
        if request.subscription:
            subscription = Subscription(
                plan=request.subscription.plan,
                max_users=request.subscription.max_users,
                max_sheets_per_month=request.subscription.max_sheets_per_month,
                features=request.subscription.features,
            )

        # Build settings
        settings = InstitutionSettings()
        if request.settings:
            branding = Branding()
            if request.settings.branding:
                branding = Branding(
                    logo=request.settings.branding.logo,
                    primary_color=request.settings.branding.primary_color,
                    secondary_color=request.settings.branding.secondary_color,
                )

            settings = InstitutionSettings(
                timezone=request.settings.timezone,
                date_format=request.settings.date_format,
                default_language=request.settings.default_language,
                branding=branding,
                passing_percentage=request.settings.passing_percentage,
                negative_marking=request.settings.negative_marking,
                negative_mark_value=request.settings.negative_mark_value,
            )

        # Create institution
        institution = Institution(
            name=request.name,
            slug=request.slug.lower(),
            code=request.code.upper(),
            type=request.type,
            contact=contact,
            subscription=subscription,
            settings=settings,
            status=InstitutionStatus.TRIAL,
            created_by=str(created_by.id),
        )

        await institution.insert()
        logger.info(f"Institution created: {institution.name} ({institution.code})")
        return institution

    @staticmethod
    async def update(
        institution_id: str,
        request: InstitutionUpdateRequest
    ) -> Institution:
        """Update institution."""
        institution = await InstitutionService.get_by_id(institution_id)

        if request.name:
            institution.name = request.name

        if request.type:
            institution.type = request.type

        if request.contact:
            if request.contact.email:
                institution.contact.email = request.contact.email
            if request.contact.phone is not None:
                institution.contact.phone = request.contact.phone
            if request.contact.address:
                if not institution.contact.address:
                    institution.contact.address = Address()
                if request.contact.address.street is not None:
                    institution.contact.address.street = request.contact.address.street
                if request.contact.address.city is not None:
                    institution.contact.address.city = request.contact.address.city
                if request.contact.address.state is not None:
                    institution.contact.address.state = request.contact.address.state
                if request.contact.address.country is not None:
                    institution.contact.address.country = request.contact.address.country
                if request.contact.address.zip_code is not None:
                    institution.contact.address.zip_code = request.contact.address.zip_code

        if request.subscription:
            institution.subscription.plan = request.subscription.plan
            institution.subscription.max_users = request.subscription.max_users
            institution.subscription.max_sheets_per_month = request.subscription.max_sheets_per_month
            institution.subscription.features = request.subscription.features

        if request.settings:
            institution.settings.timezone = request.settings.timezone
            institution.settings.date_format = request.settings.date_format
            institution.settings.default_language = request.settings.default_language
            institution.settings.passing_percentage = request.settings.passing_percentage
            institution.settings.negative_marking = request.settings.negative_marking
            institution.settings.negative_mark_value = request.settings.negative_mark_value

            if request.settings.branding:
                if not institution.settings.branding:
                    institution.settings.branding = Branding()
                institution.settings.branding.logo = request.settings.branding.logo
                institution.settings.branding.primary_color = request.settings.branding.primary_color
                institution.settings.branding.secondary_color = request.settings.branding.secondary_color

        if request.status:
            institution.status = request.status

        await institution.save_with_timestamp()
        logger.info(f"Institution updated: {institution.code}")
        return institution

    @staticmethod
    async def update_status(institution_id: str, status: str) -> Institution:
        """Update institution status."""
        institution = await InstitutionService.get_by_id(institution_id)

        valid_statuses = [
            InstitutionStatus.ACTIVE,
            InstitutionStatus.SUSPENDED,
            InstitutionStatus.TRIAL,
            InstitutionStatus.PENDING,
        ]

        if status not in valid_statuses:
            raise BadRequestError(f"Invalid status. Must be one of: {valid_statuses}")

        institution.status = status
        await institution.save_with_timestamp()
        logger.info(f"Institution status updated: {institution.code} -> {status}")
        return institution

    @staticmethod
    async def delete(institution_id: str) -> bool:
        """Delete institution."""
        institution = await InstitutionService.get_by_id(institution_id)

        # Check if institution has users
        user_count = await User.find(User.institution_id == institution.id).count()
        if user_count > 0:
            raise BadRequestError(
                f"Cannot delete institution with {user_count} users. "
                "Please delete or reassign users first."
            )

        await institution.delete()
        logger.info(f"Institution deleted: {institution.code}")
        return True

    @staticmethod
    async def get_stats(institution_id: str) -> InstitutionStatsResponse:
        """Get institution statistics."""
        institution = await InstitutionService.get_by_id(institution_id)

        # Count users
        total_users = await User.find(User.institution_id == institution.id).count()

        active_users = await User.find(
            User.institution_id == institution.id,
            User.status == UserStatus.ACTIVE
        ).count()

        # TODO: Implement actual test and sheet counts when those models exist
        total_tests = 0
        total_sheets_processed = 0
        sheets_this_month = 0

        return InstitutionStatsResponse(
            total_users=total_users,
            total_tests=total_tests,
            total_sheets_processed=total_sheets_processed,
            active_users=active_users,
            sheets_this_month=sheets_this_month,
        )

    @staticmethod
    async def create_admin_user(
        institution_id: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str
    ) -> User:
        """Create an admin user for an institution."""
        from app.models.user import UserProfile

        institution = await InstitutionService.get_by_id(institution_id)

        # Check email uniqueness
        existing = await User.find_one(User.email == email.lower())
        if existing:
            raise AlreadyExistsError("User", "email", email)

        user = User(
            email=email.lower(),
            password_hash=get_password_hash(password),
            institution_id=institution.id,
            profile=UserProfile(
                first_name=first_name,
                last_name=last_name,
            ),
            role=UserRole.INSTITUTION_ADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True,
        )

        await user.insert()
        logger.info(f"Admin user created for {institution.code}: {email}")
        return user
