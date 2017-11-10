# Define SCL name
%{!?scl_name_prefix: %global scl_name_prefix sclo-}
%{!?scl_name_base: %global scl_name_base postgresql}

%{!?version_major: %global version_major 10}

%{!?scl_name_version: %global scl_name_version %{version_major}}
%{!?scl: %global scl %{scl_name_prefix}%{scl_name_base}%{scl_name_version}}

# Turn on new layout -- prefix for packages and location
# for config and variable files
# This must be before calling %%scl_package
%{!?nfsmountable: %global nfsmountable 1}

# Define SCL macros
%{?scl_package:%scl_package %{scl}}

# do not produce empty debuginfo package
%global debug_package %{nil}

Summary: Package that installs %{scl}
Name: %{scl}
Version: 3.0.1
Release: 2%{?dist}
License: GPLv2+
Group: Applications/File
Source0: README
Source1: LICENSE
Requires: scl-utils
Requires: %{?scl_prefix}postgresql-server
BuildRequires: scl-utils-build help2man scl-utils-build-helpers

%description
This is the main package for %{scl} Software Collection, which installs
necessary packages to use PostgreSQL %{version_major} server.
Software Collections allow to install more versions of the same
package by using alternative directory structure.
Install this package if you want to use PostgreSQL %{version_major}
server on your system.


%package runtime
Summary: Package that handles %{scl} Software Collection.
Group: Applications/File
Requires: scl-utils
Requires(post): policycoreutils-python libselinux-utils

%description runtime
Package shipping essential scripts to work with %{scl} Software Collection.


%package build
Summary: Package shipping basic build configuration
Group: Applications/File
Requires: scl-utils-build scl-utils-build-helpers

%description build
Package shipping essential configuration macros to build %{scl} Software
Collection or packages depending on %{scl} Software Collection.


%package scldevel
Summary: Package shipping development files for %{scl}
%if 0%{?rhel} == 6
# implicitly required on RHEL7+, rhbz#1478831
%{?scl_runtime:Requires: %scl_runtime}
%endif

%description scldevel
Package shipping development files, especially usefull for development of
packages depending on %{scl} Software Collection.


%if 0%{?scl_syspaths_metapackage:1}
%scl_syspaths_metapackage
Requires: %{?scl_prefix}postgresql-syspaths
Requires: %{?scl_prefix}postgresql-server-syspaths
Requires: %{?scl_prefix}postgresql-contrib-syspaths

%scl_syspaths_metapackage_description
%endif


%prep
%setup -c -T

%if 0%{!?fedora:1} && 0%{?rhel} <= 7
%global _compat_scl 1
%endif

%global _scl_enable_script %{?_compat_scl:enable}%{!?_compat_scl:%{?scl}}

%define _compat_scl_env_adjust() %{lua:                         \
var = rpm.expand("%1")                                          \
if tonumber(rpm.expand('0%{?_compat_scl}'), 10) == 0 then       \
    print(rpm.expand("prepend-path %1 %2"))                     \
elseif var == "MANPATH" then                                    \
    print(rpm.expand('export %1=%2:$%1'))                       \
elseif var == "JAVACONFDIRS" then                               \
    print(rpm.expand('export %1=%2:${%1:-/etc/java}'))          \
elseif var == "XDG_CONFIG_DIRS" then                            \
    print(rpm.expand('export %1=%2:${%1:-/etc/xdg}'))           \
elseif var == "XDG_DATA_DIRS" then                              \
    print(rpm.expand('export %1=%2:${%1:-/usr/local/share:/usr/share}')) \
else                                                            \
    print(rpm.expand('export %1=%2${%1:+:$%1}'))                \
end                                                             \
}                                                               \
%nil

# This section generates README file from a template and creates man page
# from that file, expanding RPM macros in the template file.
cat <<'EOF' | tee README
%{expand:%(cat %{SOURCE0})}
EOF

# copy the license file so %%files section sees it
cp %{SOURCE1} .


%build
# generate a helper script that will be used by help2man
cat <<'EOF' | tee h2m_helper
#!/bin/bash
[ "$1" == "--version" ] && echo "%{?scl_name} %{version} Software Collection" || cat README
EOF
chmod a+x h2m_helper

# generate the man page
help2man -N --section 7 ./h2m_helper -o %{?scl_name}.7


%install
%{?scl_install}

# create and own dirs not covered by %%scl_install and %%scl_files
%if 0%{?rhel} >= 7 || 0%{?fedora} >= 15
mkdir -p %{buildroot}%{_mandir}/man{1,7,8}
%else
mkdir -p %{buildroot}%{_datadir}/aclocal
%endif

# create enable scriptlet that sets correct environment for collection
cat <<\EOF | tee -a %{buildroot}%{?_scl_scripts}/%_scl_enable_script
%if 0%{!?_compat_scl:1}
#%%Module1.0
prepend-path X_SCLS %{scl}

%endif
# For binaries
%_compat_scl_env_adjust PATH  %_bindir
# For header files
%_compat_scl_env_adjust CPATH %_includedir
# For libraries during build
%_compat_scl_env_adjust LIBRARY_PATH %_libdir
# For libraries during linking
%_compat_scl_env_adjust LD_LIBRARY_PATH %_libdir
# For man pages; empty field makes man to consider also standard path
%_compat_scl_env_adjust MANPATH %_mandir
# For Java Packages Tools to locate java.conf
%_compat_scl_env_adjust JAVACONFDIRS %_sysconfdir/java
# For pkg-config
%_compat_scl_env_adjust PKG_CONFIG_PATH %_libdir/pkgconfig
EOF

# Automatically generate enable script when needed.
%{?scl_enable_script}

cat << EOF | tee -a %{buildroot}%{_root_sysconfdir}/rpm/macros.%{scl_name_base}-scldevel
# macros to be used by packages depended on %scl collection
%%scl_%{scl_name_base} %{scl}
%%scl_prefix_%{scl_name_base} %{?scl_prefix}
EOF

%if 0%{?rhel} == 6
cat <<EOF >>%{buildroot}%{_root_sysconfdir}/rpm/macros.%{scl}-config
# hack to minimize patching of postgresql.spec for RHEL6
%%_pkgdocdir %%{_docdir}/%%{name}-%%{version}
EOF
%endif

# install generated man page
mkdir -p %{buildroot}%{_mandir}/man7/
install -m 644 %{?scl_name}.7 %{buildroot}%{_mandir}/man7/%{?scl_name}.7


%post runtime
# Simple copy of context from system root to SCL root.
# In case new version needs some additional rules or context definition,
# it needs to be solved in base system.
# semanage does not have -e option in RHEL-5, so we would
# have to have its own policy for collection.
semanage fcontext -a -e / %{?_scl_root} >/dev/null 2>&1 || :
semanage fcontext -a -e %{_root_sysconfdir} %{_sysconfdir} >/dev/null 2>&1 || :
semanage fcontext -a -e %{_root_localstatedir} %{_localstatedir} >/dev/null 2>&1 || :

selinuxenabled && load_policy || :
restorecon -R %{?_scl_root} >/dev/null 2>&1 || :
restorecon -R %{_sysconfdir} >/dev/null 2>&1 || :
restorecon -R %{_localstatedir} >/dev/null 2>&1 || :


%files


%if 0%{?rhel} >= 7 || 0%{?fedora} >= 15
%files runtime -f filesystem
%else
%files runtime
%{_datadir}/aclocal
%endif
%doc README LICENSE
%{?scl_files}


%files build
%doc LICENSE
%{_root_sysconfdir}/rpm/macros.%{scl}-config


%files scldevel
%doc LICENSE
%{_root_sysconfdir}/rpm/macros.%{scl_name_base}-scldevel


%{?scl_syspaths_metapackage:%files syspaths}


%changelog
* Fri Nov 10 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0.1-2
- bootstrap, depend on scl_runtime only if it is defined (when the
  scl-utils-build is in buildroot, required by implicit sclo-postgresql10-build

* Fri Nov 10 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0.1-1
- update to sclo-postgresql10

* Mon Sep 04 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-12
- don't set XDG_* variables, per rhbz#1464084

* Wed Aug 16 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-11
- scldevel subpackage to depend on runtime subpackage

* Mon Jun 26 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-9
- require contrib-syspaths by syspaths

* Wed Jun 21 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-8
- rebuild for description/summary changes in *-syspaths

* Wed Jun 21 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-7
- fix hack with _pkgdocdir; _pkgdocdir was defined every second build because we
  defined the _pkgdocdir for ourselves

* Wed Jun 21 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-6
- add syspaths metapackage

* Tue Jun 20 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-5
- first build with scl_name_prefix 'rh-'

* Tue Apr 18 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-4
- add space after _compat_scl_env_adjust, the newline is not automatically
  added on RHEL6

* Tue Apr 18 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-3
- airier spec file

* Wed Apr 12 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-2
- scl-utils v2 fix

* Thu Apr 06 2017 Pavel Raiskup <praiskup@redhat.com> - 3.0-1
- bump version against scl 3

* Wed Jul 27 2016 Pavel Raiskup <praiskup@redhat.com> - 2.2-3
- rebuild for s390x

* Thu Feb 11 2016 Honza Horak <hhorak@redhat.com> - 2.2-2
- Rebuild with newer scl-utils

* Fri Jan 29 2016 Pavel Kajaba <pkajaba@redhat.com> - 2.2-1
- Release bump

* Fri Mar 20 2015 Pavel Raiskup <praiskup@redhat.com> - 2.0-9
- move the postgresql-ctl context definition to main package

* Thu Mar 19 2015 Pavel Raiskup <praiskup@redhat.com> - 2.0-8
- fix SELinux context on starting binaries once more

* Wed Mar 18 2015 Pavel Raiskup <praiskup@redhat.com> - 2.0-7
- merge rhel6 & rhel7 rh-postgresql94 branches

* Wed Mar 18 2015 Pavel Raiskup <praiskup@redhat.com> - 2.0-6
- fix SELinux context on starting binaries
- rebuild for scl-utils change (#1200057)

* Wed Feb 18 2015 Honza Horak <hhorak@redhat.com> - 2.0-5
- Remove NFS register feature for questionable usage for DBs

* Thu Jan 29 2015 Jozef Mlich <jmlich@redhat.com> - 2.0-4
- %{_unitdir} is available only in RHEL7

* Mon Jan 26 2015 Honza Horak <hhorak@redhat.com> - 2.0-3
- Do not set selinux context  scl root during scl register

* Mon Jan 26 2015 Honza Horak <hhorak@redhat.com> - 2.0-2
- Use cat for README expansion, rather than include macro

* Sat Jan 17 2015 Honza Horak <hhorak@redhat.com>
- Apply many changes for new generation

* Mon Oct 13 2014 Honza Horak <hhorak@redhat.com> - 1.1-21
- Rebuild for s390x
  Resolves: #1152432

* Mon Mar 31 2014 Honza Horak <hhorak@redhat.com> - 1.1-20
- Fix path typo in README
  Related: #1061456

* Wed Feb 19 2014 Jozef Mlich <jmlich@redhat.com> - 1.1-19
- Release bump (and cherry pick from rhscl-1.1-postgresql92-rhel-7)
  Resloves: #1061456 

* Thu Feb 13 2014 Jozef Mlich <jmlich@redhat.com> - 1.1-18
- Resolves: #1058611 (postgresql92-build needs to depend
  on scl-utils-build)
- Add LICENSE, README and postgresql92.7 man page
  Resloves: #1061456 

* Wed Feb 12 2014 Honza Horak <hhorak@redhat.com> - 1.1-17
- Add -scldevel subpackage
  Resolves: #1063359

* Wed Dec 18 2013 Jozef Mlich <jmlich@redhat.com> 1-17
- release bump 
  Resolves #1038693

* Tue Nov 26 2013 Jozef Mlich <jmlich@redhat.com> 1-16
- By default, patch(1) creates backup files when chunks apply with offsets.
  Turn that off to ensure such files don't get included in RPMs.

* Fri Nov 22 2013 Honza Horak <hhorak@redhat.com> 1-15
- Rename variable to match postgresql package

* Mon Nov 18 2013 Jozef Mlich <jmlich@redhat.com> 1-14
- release bump

* Wed Oct  9 2013 Jozef Mlich <jmlich@redhat.com> 1-13
- release bump to scl 1.1

* Wed May 22 2013 Honza Horak <hhorak@redhat.com> 1-12
- Run semanage on whole root, BZ#956981 is fixed now
- Require semanage utility to be installed for -runtime package
- Fix MANPATH definition, colon in the end is correct (it means default)
  Resolves: BZ#966382

* Fri May  3 2013 Honza Horak <hhorak@redhat.com> 1-11
- Run semanage for all directories separately, since it has
  problems with definition for whole root

* Thu May  2 2013 Honza Horak <hhorak@redhat.com> 1-10
- Handle context of the init script
- Add better descriptions for packages

* Fri Apr 26 2013 Honza Horak <hhorak@redhat.com> 1-9
- fix escaping in PATH variable definition

* Mon Apr  8 2013 Honza Horak <hhorak@redhat.com> 1-8
- Don't require policycoreutils-python in RHEL-5 or older
- Require postgresql-server from the collection as main package
- Build separately on all arches
- Fix Environment variables definition

* Wed Feb 20 2013 Honza Horak <hhorak@redhat.com> 1-7
- Use %%setup macro to create safer build environment

* Fri Nov 09 2012 Honza Horak <hhorak@redhat.com> 1-6
- rename spec file to correspond with package name

* Thu Nov 08 2012 Honza Horak <hhorak@redhat.com> 1-5
- Mark service-environment as a config file

* Thu Oct 25 2012 Honza Horak <hhorak@redhat.com> 1-5
- create service-environment file to hold information about all collections,
  that should be enabled when service is starting
- added policycoreutils-python for semanage -e

* Thu Oct 18 2012 Honza Horak <hhorak@redhat.com> 1-3
- copy SELinux context from core mysql files

* Wed Oct 03 2012 Honza Horak <hhorak@redhat.com> 1-2
- update to postgresql-9.2 and rename to postgresql92

* Mon Mar 19 2012 Honza Horak <hhorak@redhat.com> 1-1
- initial packaging

