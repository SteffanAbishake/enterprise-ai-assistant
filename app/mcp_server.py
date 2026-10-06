"""Local subprocess only; never expose this unauthenticated mock server over a network."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Mock Enterprise Services")


@mcp.tool()
def service_catalog(service: str) -> dict:
    """Read fictional service ownership. Only the payments service is allowed."""
    if service != "payments":
        raise ValueError("Unknown service")
    return {
        "id": "service-payments",
        "service": "payments",
        "owner": "Payments Operations",
        "text": "Payments Operations owns the payments service. Escalate through the on-call queue.",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
