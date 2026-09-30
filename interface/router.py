class Router:
    def __init__(self, container, app):
        self.container = container
        self.app = app

        self.views = {}
        self.current_view = None

    def show(self, view_id):
        if self.current_view:
            self.current_view.on_hide()
            self.current_view.pack_forget()

        if view_id not in self.views:
            definition = self.app.registry.get(view_id)

            self.views[view_id] = definition.view(
                self.container,
                self.app,
            )

        view = self.views[view_id]

        view.pack(
            fill="both",
            expand=True,
        )

        view.on_show()
        self.current_view = view