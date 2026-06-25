from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class BootstrapperSpec:
    name: str
    handler: str
    description: str = ""
    stack: str = ""


@dataclass
class StackSpec:
    name: str
    description: str = ""


@dataclass
class ConsolePageSpec:
    key: str
    title: str
    route: str
    import_module: str = ""
    export: str = "default"
    sidebar: bool = True
    render: str = "component"
    asset_dir: str = ""
    entrypoint: str = "index.html"


@dataclass
class ProjectViewSpec:
    stack: str
    import_module: str
    export: str = "default"
    title: str = ""


@dataclass
class SkillSpec:
    name: str
    source: str


@dataclass
class PluginCapabilities:
    bootstrappers: list[BootstrapperSpec] = field(default_factory=list)
    stacks: list[StackSpec] = field(default_factory=list)
    console_pages: list[ConsolePageSpec] = field(default_factory=list)
    project_views: list[ProjectViewSpec] = field(default_factory=list)
    skills: list[SkillSpec] = field(default_factory=list)
    django_url_modules: list[str] = field(default_factory=list)
    console_npm_packages: list[str] = field(default_factory=list)


@dataclass
class PluginRecord:
    plugin_id: str
    display_name: str
    version: str
    package_name: str
    source_type: str
    source: str
    source_path: str
    entrypoint_name: str
    entrypoint_value: str
    requirement: str
    github_url: str = ""
    ref: str = ""
    commit_sha: str = ""
    capabilities: PluginCapabilities = field(default_factory=PluginCapabilities)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PluginRecord:
        caps_data = data.get("capabilities", {})
        caps = PluginCapabilities(
            bootstrappers=[
                BootstrapperSpec(**item) for item in caps_data.get("bootstrappers", [])
            ],
            stacks=[StackSpec(**item) for item in caps_data.get("stacks", [])],
            console_pages=[
                ConsolePageSpec(**item) for item in caps_data.get("console_pages", [])
            ],
            project_views=[
                ProjectViewSpec(**item) for item in caps_data.get("project_views", [])
            ],
            skills=[SkillSpec(**item) for item in caps_data.get("skills", [])],
            django_url_modules=list(caps_data.get("django_url_modules", [])),
            console_npm_packages=list(caps_data.get("console_npm_packages", [])),
        )
        payload = {**data, "capabilities": caps}
        return cls(**payload)


@dataclass
class PluginRegistry:
    plugins: list[PluginRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"plugins": [plugin.to_dict() for plugin in self.plugins]}

    @classmethod
    def from_dict(cls, data: dict) -> PluginRegistry:
        plugins = [PluginRecord.from_dict(item) for item in data.get("plugins", [])]
        return cls(plugins=plugins)

    def get(self, plugin_id: str) -> PluginRecord | None:
        for plugin in self.plugins:
            if plugin.plugin_id == plugin_id:
                return plugin
        return None
