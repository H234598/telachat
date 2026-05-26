%global appname telachat
%global appversion %{?_version}%{!?_version:0.71.0}

Name:           %{appname}
Version:        %{appversion}
Release:        1%{?dist}
Summary:        Local configurable AI chat client
License:        MIT
URL:            https://github.com/H234598/telachat
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  python3 >= 3.11
Requires:       python3 >= 3.11

%description
Telachat is a local CLI and native desktop chat client for configurable
OpenAI-compatible providers. It stores history locally and ships a Tk and GTK
frontend.

%prep
%autosetup

%build
python3 -m zipapp src -p "/usr/bin/env python3" -o %{appname}.pyz

%install
install -Dm0755 %{appname}.pyz %{buildroot}%{_libexecdir}/%{appname}/%{appname}.pyz

mkdir -p %{buildroot}%{_bindir}
for wrapper in telachat telachat-tk telachat-gtk telachat-gui; do
    sed "s|@TELACHAT_PYZ@|%{_libexecdir}/%{appname}/%{appname}.pyz|g" \
        packaging/linux/wrappers/${wrapper}.in > %{buildroot}%{_bindir}/${wrapper}
    chmod 0755 %{buildroot}%{_bindir}/${wrapper}
done

install -Dm0644 docs/man/telachat.1 %{buildroot}%{_mandir}/man1/telachat.1
install -Dm0644 docs/man/telachat-tk.1 %{buildroot}%{_mandir}/man1/telachat-tk.1
install -Dm0644 docs/man/telachat-gtk.1 %{buildroot}%{_mandir}/man1/telachat-gtk.1
install -Dm0644 src/telachat/assets/icons-png/06_round_orange_cat_icon.png \
    %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/telachat.png
mkdir -p %{buildroot}%{_datadir}/applications
sed "s|@TELACHAT_EXEC@|telachat-gui|g" packaging/linux/telachat.desktop.in \
    > %{buildroot}%{_datadir}/applications/telachat.desktop

%files
%license LICENSE
%doc README.md CHANGELOG.md docs/RESEARCH.md docs/TESTING.md
%{_bindir}/telachat
%{_bindir}/telachat-tk
%{_bindir}/telachat-gtk
%{_bindir}/telachat-gui
%{_libexecdir}/%{appname}/%{appname}.pyz
%{_datadir}/applications/telachat.desktop
%{_datadir}/icons/hicolor/256x256/apps/telachat.png
%{_mandir}/man1/telachat.1*
%{_mandir}/man1/telachat-tk.1*
%{_mandir}/man1/telachat-gtk.1*

%changelog
* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.73.0-1
- Add folder-backend slash command for folder default backends.
- Keep CLI folder prompt/context updates live for the next chat request.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.72.0-1
- Add folder-context slash command for folder context notes.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.71.0-1
- Add folder-prompt slash command alias for folder prompts.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.70.5-1
- Clarify Tk and GTK folder prompt action wording.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.70.4-1
- Opt every GitHub Actions workflow with JavaScript actions into Node 24.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.70.3-1
- Opt Linux GitHub Actions JavaScript steps into Node 24.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.70.2-1
- Normalize legacy folder prompts that already contain folder context.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.70.1-1
- Keep folder context notes out of editable GUI folder prompts.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.70.0-1
- Add per-folder context notes for new chats and portable exports.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.69.1-1
- Handle non-UTF-8 import files without tracebacks.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.69.0-1
- Add portable folder ZIP bundles for export-folder/import-folder.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.68.0-1
- Add latest assistant response copy button to Tk and GTK.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.67.1-1
- Respect profile filters in redacted config TOML output.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.67.0-1
- Add redacted config TOML view to config-check.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.66.0-1
- Remember recent custom prompt-template values in GUI sessions.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.65.1-1
- Add safe Linux installer smoke target for temporary desktop checks.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.65.0-1
- Add shared context completion for GUI slash commands.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.64.1-1
- Use one Tk dialog for prompt-template custom variables.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.64.0-1
- Add GUI dialogs for prompt-template custom variables.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.63.0-1
- Add custom prompt-template variables for CLI template asks.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.62.0-1
- Add CLI prompt-template preview via templates --show.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.61.0-1
- Add prompt-template preview metadata shared by Tk and GTK.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.60.0-1
- Add copyable prompt-template preview windows for Tk and GTK.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.59.0-1
- Add GUI save-as-prompt-template actions for Tk and GTK.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.58.0-1
- Add prompt-template create, rename, and delete management.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.57.1-1
- Restore visible new-chat sidebar action and keep Tk session list row sizing aligned.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.57.0-1
- Add shared shortcut help for CLI and GUI prompts.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.56.0-1
- Add compact GUI chat headers with arrow pane toggles.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.55.0-1
- Add copyable GUI error windows for provider failures.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.54.3-1
- Skip Linux shell launcher execution on Windows CI and preserve Snap runtime mount paths.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.54.2-1
- Make RPM build directory setup POSIX-sh compatible.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.54.1-1
- Make RPM builds portable across non-RPM CI hosts.

* Tue May 26 2026 Teladi <teladi@example.invalid> - 0.54.0-1
- Add Linux installer, desktop entry, and RPM packaging.
