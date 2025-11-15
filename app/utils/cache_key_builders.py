from starlette.requests import Request


def achievement_images_key_builder(
    func,
    namespace: str = "",
    *,
    request: Request | None = None,
    response=None,
    **kwargs,
) -> str:
    achievement_id = None
    if request:
        achievement_id = request.path_params.get("achievement_id")
    if not achievement_id:
        achievement_id = kwargs.get("achievement_id")

    return f"{namespace}:{achievement_id}"


def volunteer_received_achievements_key_builder(
    func,
    namespace: str = "",
    *,
    request: Request | None = None,
    response=None,
    **kwargs,
) -> str:
    volunteer_id = None
    if request:
        volunteer_id = request.path_params.get("volunteer_id")
    if not volunteer_id:
        volunteer_id = kwargs.get("volunteer_id")
    return f"{namespace}:{volunteer_id}"
