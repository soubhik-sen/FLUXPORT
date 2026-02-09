from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

#from app.api.routers import dynamic_search
from app.api.routers.users import router as users_router
from app.api.routers.masteraddr import router as masteraddr_router
from app.api.routers.forwarder import router as forwarder_router
from app.api.routers.supplier import router as supplier_router
from app.api.routers.partner_master import router as partner_master_router
from app.api.routers.partner_type import router as partner_type_router
from app.api.routers.customer_master import router as customer_master_router
from app.api.routers.customer_type import router as customer_type_router
from app.api.routers.customer_forwarder import router as customer_forwarder_router
from app.api.routers.forwarder_port import router as forwarder_port_router
from app.api.routers.customer_branch import router as customer_branch_router
from app.api.routers.material_master import router as material_master_router
from app.api.routers.roles import router as roles_router
from app.api.routers.permissions import router as permissions_router
from app.api.routers.role_permissions import router as role_permissions_router
from app.api.routers.user_roles import router as user_roles_router
from app.api.routers.user_departments import router as user_departments_router
from app.api.routers.user_countries import router as user_countries_router
from app.api.routers.user_attributes import router as user_attributes_router
from app.api.routers.domains import router as domains_router
from app.api.routers.object_types import router as object_types_router
from app.api.routers.user_customer_link import router as user_customer_link_router
from app.api.routers.user_partner_link import router as user_partner_link_router
from app.api.routers.metadata import router as metadata_router
from app.api.routers.user_profile import router as user_profile_router
from app.api.routers.access_queries import router as access_queries_router
from app.api.routers.number_range import router as NumberRangeCreate
from app.api.routers.workflow_rules import router as workflow_rules_router

from app.api.v1.endpoints.api import api_router
from app.api.v1.endpoints import reports

app = FastAPI(title="FLUXPORT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development; specify your flutter domain for production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
#app.include_router(dynamic_search.router, tags=["dynamic"])
app.include_router(masteraddr_router)
app.include_router(forwarder_router)
app.include_router(supplier_router)
app.include_router(partner_master_router)
app.include_router(partner_type_router)
app.include_router(customer_master_router)
app.include_router(customer_type_router)
app.include_router(customer_forwarder_router)
app.include_router(forwarder_port_router)
app.include_router(customer_branch_router)
app.include_router(material_master_router)
app.include_router(roles_router)
app.include_router(permissions_router)
app.include_router(role_permissions_router)
app.include_router(user_roles_router)
app.include_router(user_departments_router)
app.include_router(user_countries_router)
app.include_router(user_attributes_router)
app.include_router(domains_router)
app.include_router(object_types_router)
app.include_router(user_customer_link_router)
app.include_router(user_partner_link_router)
app.include_router(metadata_router)
app.include_router(user_profile_router)
app.include_router(access_queries_router)
app.include_router(workflow_rules_router)

app.include_router(api_router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(NumberRangeCreate)

@app.get("/health")
def health():
    return {"status": "up"}
