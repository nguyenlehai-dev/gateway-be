from fastapi import APIRouter

from app.api.v1.endpoints import api_functions, auth, gateway, gateway_keys, gateway_requests, pool_api_keys, pools, users, vendors

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(gateway_keys.router, prefix="/gateway-keys", tags=["gateway-keys"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
api_router.include_router(pools.router, prefix="/pools", tags=["pools"])
api_router.include_router(pool_api_keys.router, prefix="/pool-api-keys", tags=["pool-api-keys"])
api_router.include_router(api_functions.router, prefix="/api-functions", tags=["api-functions"])
api_router.include_router(gateway.router, prefix="/gateway", tags=["gateway"])
api_router.include_router(gateway_requests.router, prefix="/gateway/requests", tags=["gateway-requests"])
