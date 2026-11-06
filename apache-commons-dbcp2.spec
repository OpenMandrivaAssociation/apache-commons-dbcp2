Name:		apache-commons-dbcp2
Version:	2.14.0
Release:	1
Summary:	Database connection pooling
Group:		Development/Java
License:	ASL 2.0
URL:		https://commons.apache.org/proper/commons-dbcp/
Source0:	https://github.com/apache/commons-dbcp/archive/refs/tags/rel/commons-dbcp-%{version}.tar.gz#/commons-dbcp-%{version}.tar.gz

BuildArch:	noarch
# The site-checkout profile is active when site-content is absent, and
# antrun is on the sysjar keep list.
%global sysjar_drops --drop org.apache.maven.plugins:maven-antrun-plugin
BuildRequires:	mvn(org.apache.commons:commons-parent:pom::)
BuildRequires:	mvn(org.apache:apache:pom::)
BuildRequires:	mvn(org.apache.commons:commons-pool2)
BuildRequires:	mvn(commons-logging:commons-logging)
# Managed connections import javax.transaction. The upstream coordinate
# is jakarta.transaction-api 1.3.3; the system jar is JTA 1.1.
BuildRequires:	mvn(javax.transaction:jta)
# Literal, so the first rpmbuild -bs records them before sysjar is installed.
BuildRequires:	maven
BuildRequires:	java-current-devel
BuildSystem:	maven
BuildOption(install):	--file-name commons-dbcp2 --link %{name}

%description
Apache Commons DBCP pools JDBC connections on top of Commons Pool.
2.14.0 adds a char[] password setter and makes validation queries time
out on the shared and per-user pools. Managed connections use the
system JTA 1.1 API. Tests are skipped.

%prep
%autosetup -n commons-dbcp-rel-commons-dbcp-%{version}
# Test dependencies are not packaged. The reporting plugins pull in
# jakarta.transaction-api as well. Assembly, Surefire, SCM publish, and
# Javadoc are not part of this build.
python - <<'PY'
import xml.etree.ElementTree as ET
from pathlib import Path

ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

def local(tag):
    return tag.rsplit("}", 1)[-1]

def find_child(elem, name):
    for child in elem:
        if local(child.tag) == name:
            return child
    return None

drop_plugins = {
    "maven-surefire-plugin",
    "maven-assembly-plugin",
    "maven-scm-publish-plugin",
    "maven-javadoc-plugin",
}

path = Path("pom.xml")
tree = ET.parse(path)
root = tree.getroot()
removed_reporting = 0
for child in list(root):
    if local(child.tag) == "reporting":
        root.remove(child)
        removed_reporting += 1
deps = find_child(root, "dependencies")
if deps is None:
    raise SystemExit("dependencies missing")
removed_tests = 0
rewritten = False
for child in list(deps):
    if local(child.tag) != "dependency":
        continue
    group = artifact = scope = ""
    version = None
    for item in child:
        name = local(item.tag)
        if name == "groupId":
            group = (item.text or "").strip()
        elif name == "artifactId":
            artifact = (item.text or "").strip()
        elif name == "scope":
            scope = (item.text or "").strip()
        elif name == "version":
            version = item
    if scope == "test":
        deps.remove(child)
        removed_tests += 1
        continue
    if group == "jakarta.transaction" and artifact == "jakarta.transaction-api":
        for item in child:
            name = local(item.tag)
            if name == "groupId":
                item.text = "javax.transaction"
            elif name == "artifactId":
                item.text = "jta"
        if version is None:
            raise SystemExit("jta version missing")
        version.text = "1.1.1"
        rewritten = True
build = find_child(root, "build")
plugins = find_child(build, "plugins") if build is not None else None
if plugins is None:
    raise SystemExit("plugins missing")
removed = []
for child in list(plugins):
    if local(child.tag) != "plugin":
        continue
    artifact = ""
    for item in child:
        if local(item.tag) == "artifactId":
            artifact = (item.text or "").strip()
    if artifact in drop_plugins:
        plugins.remove(child)
        removed.append(artifact)
if (
    removed_reporting != 1
    or removed_tests != 11
    or not rewritten
    or sorted(removed) != sorted(drop_plugins)
):
    raise SystemExit(
        f"reporting={removed_reporting} tests={removed_tests} "
        f"jta={rewritten} removed={removed}"
    )
tree.write(path, encoding="UTF-8", xml_declaration=True)
PY

%files -f .mfiles
%doc LICENSE.txt NOTICE.txt RELEASE-NOTES.txt README.md
