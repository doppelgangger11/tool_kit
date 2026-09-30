from dataclasses import dataclass


@dataclass
class ViewDefinition:
    id: str
    title: str
    icon: str
    group: str
    view: type


class ViewRegistry:

    def __init__(self):
        self._views = {}

    def register(
        self,
        id: str,
        title: str,
        view: type,
        icon: str = "",
        group: str = "TOOLS",
    ):
        if id in self._views:
            raise ValueError(
                f"View '{id}' already registered."
            )

        self._views[id] = ViewDefinition(
            id=id,
            title=title,
            icon=icon,
            group=group,
            view=view,
        )

    def get(self, view_id):
        return self._views[view_id]

    def groups(self):
        result = {}

        for view in self._views.values():
            result.setdefault(
                view.group,
                []
            ).append(view)

        return result