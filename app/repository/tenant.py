from typing import Optional

from app.models import Tenant

class TenantRepository:

    @staticmethod
    def get_tenant_by_id(tenant_id: int) -> Optional[Tenant]:
        return Tenant.query.get(tenant_id)