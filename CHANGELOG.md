# Changelog

## [0.4.1](https://github.com/Apollogeddon/forgepy/compare/v0.4.0...v0.4.1) (2026-10-08)


### Bug Fixes

* **ci:** leave Dependabot's GitHub Actions updates for a person to merge ([50cead3](https://github.com/Apollogeddon/forgepy/commit/50cead34687ec160a494c98d1a659ffaad21dcfa))
* **ci:** leave Dependabot's GitHub Actions updates for a person to merge ([27d8ba7](https://github.com/Apollogeddon/forgepy/commit/27d8ba726b525f3466dfc2037e1a6d53ab2670d7))

## [0.4.0](https://github.com/Apollogeddon/forgepy/compare/v0.3.2...v0.4.0) (2026-10-08)


### Features

* scaffold projects whose scripts run on Jython 2.7 ([b23ef1a](https://github.com/Apollogeddon/forgepy/commit/b23ef1a74eb31626ea4db8e277f3387a4cda0e9d))
* scaffold projects whose scripts run on Jython 2.7 ([e594bba](https://github.com/Apollogeddon/forgepy/commit/e594bba3b7c04b61df7e0134bc1759e153fbcdbe))


### Bug Fixes

* target a Jython project's tests at the project's Python ([f6f73da](https://github.com/Apollogeddon/forgepy/commit/f6f73da3e8ed7baffbc304b56a85a85d1a91c0d7))
* target a Jython project's tests at the project's Python ([56ad4b8](https://github.com/Apollogeddon/forgepy/commit/56ad4b858549a2e8d9a19e1755718f96f444f273))

## [0.3.2](https://github.com/Apollogeddon/forgepy/compare/v0.3.1...v0.3.2) (2026-10-08)


### Bug Fixes

* auto-merge a Dependabot PR that only waits on checks nobody requires ([9a57760](https://github.com/Apollogeddon/forgepy/commit/9a57760b19a36632ef9e3c5b98aaa4945d048239))
* auto-merge a Dependabot PR that only waits on checks nobody requires ([512f56b](https://github.com/Apollogeddon/forgepy/commit/512f56bf578ed539290df4a8c3b62c5724b7b946))

## [0.3.1](https://github.com/Apollogeddon/forgepy/compare/v0.3.0...v0.3.1) (2026-10-08)


### Bug Fixes

* auto-merge Dependabot PRs through the API, so a runner needs no gh CLI ([648b71f](https://github.com/Apollogeddon/forgepy/commit/648b71f92a2d5b95131e7c53d496127da139f9d8))
* auto-merge Dependabot PRs through the API, so a runner needs no gh CLI ([49420a0](https://github.com/Apollogeddon/forgepy/commit/49420a02e6683280951dec3f79507154a1acf287))

## [0.3.0](https://github.com/Apollogeddon/forgepy/compare/v0.2.0...v0.3.0) (2026-10-08)


### Features

* **ci:** upgrade packages with known vulnerabilities on main, as forgejs's auto_patch does ([8e3efaf](https://github.com/Apollogeddon/forgepy/commit/8e3efaf78bd5dfbf7b2ffd94ff0f704662d2bd6b))


### Bug Fixes

* bump forgepy's version in the docs lock on release too ([e1b3557](https://github.com/Apollogeddon/forgepy/commit/e1b35575e441b46ef044b07b06ea503d1ba1c4cc))
* bump the version in uv.lock on release, which release-please never matched ([eac7010](https://github.com/Apollogeddon/forgepy/commit/eac7010e1679fc27bf75f92d6e13923a8297aedc))
* **ci:** add timeouts to the release-please and pages deploy jobs ([e6f8da3](https://github.com/Apollogeddon/forgepy/commit/e6f8da3f9b8dac6414701333e8ceb777867230ac))
* **ci:** don't leave the token in .git/config for jobs that never push ([793eae0](https://github.com/Apollogeddon/forgepy/commit/793eae08205ec8746d7edc63a4e5430a765308d4))
* **ci:** harden the reusable workflows and the generated ci ([327e98a](https://github.com/Apollogeddon/forgepy/commit/327e98a392ba2f2e16ec9977788b6899a0e9e0cc))
* **deps:** bump the dependencies group across 1 directory with 2 updates ([5032674](https://github.com/Apollogeddon/forgepy/commit/5032674c293d8cb14834ed7137adb8ee66e7fcdf))
* **deps:** bump the dependencies group across 1 directory with 2 updates ([797e472](https://github.com/Apollogeddon/forgepy/commit/797e4720953c91c407812edb54800ed49c563f83))
* generate ci with a concurrency rule and without secrets: inherit ([91060d6](https://github.com/Apollogeddon/forgepy/commit/91060d6303bb4c8f1cfd2fe42bac1914db3b6447))


### Documentation

* fix the test_on_push example and say what --website scaffolds ([d277e2e](https://github.com/Apollogeddon/forgepy/commit/d277e2e9f2d774112f8b3268d598fa54d7358c0b))
* link the README logo to the docs site ([6ce6cc5](https://github.com/Apollogeddon/forgepy/commit/6ce6cc5901eb89eb96c03988a0cdc88eb16bf8cc))
* link the README logo to the docs site ([af4b426](https://github.com/Apollogeddon/forgepy/commit/af4b426d437642da1a456784deb286dc7041c1d6))
* point the test_on_push example at forgepy's own service workflow ([c2c7f22](https://github.com/Apollogeddon/forgepy/commit/c2c7f22f88f5edf52b03928379cf85e2af91b0af))
* say that --website is a documentation site, not a frontend app ([f3e5b93](https://github.com/Apollogeddon/forgepy/commit/f3e5b931fd274f73f99b0b96a8be1f3e90336334))

## [0.2.0](https://github.com/Apollogeddon/forgepy/compare/v0.1.0...v0.2.0) (2026-10-05)


### Features

* add .claude, .vscode, and .github tooling (Python-native hooks, not Node) ([efd637b](https://github.com/Apollogeddon/forgepy/commit/efd637bc8c373009ea97e0e4253ed482defc70ac))
* add base, linting, build, testing, and versioning features ([62f8a12](https://github.com/Apollogeddon/forgepy/commit/62f8a1237899c12494f9c239822ccc2f63918943))
* add CLI, config, and pyproject.toml merge logic ([f0c5686](https://github.com/Apollogeddon/forgepy/commit/f0c5686e9cfd16a6a8f0d233e67c7d01e8285168))
* add Debian packaging via nfpm ([2367eee](https://github.com/Apollogeddon/forgepy/commit/2367eeea69447a37d6e615f63cc6dfc2a661e2a2))
* add Docker support for backend and website modes ([de86199](https://github.com/Apollogeddon/forgepy/commit/de86199809ec821f359508b7238a3cd3ed1e50fd))
* add filesystem abstraction and feature pipeline base ([7fd8074](https://github.com/Apollogeddon/forgepy/commit/7fd8074a4eed8889c6e23cafb637c80a139c325b))
* add forgepy sync command to refresh .forgepy/ base configs ([15414b6](https://github.com/Apollogeddon/forgepy/commit/15414b66c2dce68623679b8e951a030e339361e3))
* add GitHub Actions workflow generation and reusable workflows ([192e6b8](https://github.com/Apollogeddon/forgepy/commit/192e6b8632ca88155873794fa81b43f49d7327ec))
* add publish input to library.yml and disable it for forgepy's own CI ([49dce76](https://github.com/Apollogeddon/forgepy/commit/49dce76ed79a67cba4059404781867f81e682254))
* build every platform on a remote buildkit, on self-hosted runners without a docker daemon ([479a621](https://github.com/Apollogeddon/forgepy/commit/479a621c1b20b11b63bfcc01e1d42980b7086c0b))
* build website projects with zensical instead of mkdocs ([5ae124f](https://github.com/Apollogeddon/forgepy/commit/5ae124fa9874838363be9c380018ec414a139e03))
* **ci:** build multi-platform docker images and push to GHCR on release ([82d1036](https://github.com/Apollogeddon/forgepy/commit/82d10369c924ffa51159cbbbe030efdd52835dc3))
* **docs:** add documentation site and pages deploy to website workflow ([7a0de08](https://github.com/Apollogeddon/forgepy/commit/7a0de082f246ac480f01918148d5014d8a3e19d8))
* dogfood commit-message linting for forgepy's own repo ([242622b](https://github.com/Apollogeddon/forgepy/commit/242622b6e26fa961c73272ec5a7dfca5ec0e2f56))
* dogfood forgepy's own poe tasks and pytest.toml ([c976fcc](https://github.com/Apollogeddon/forgepy/commit/c976fcc71bdf43fcd443d21e418beb6173e207ec))
* dogfood forgepy's own ruff and pyright config ([42bcb32](https://github.com/Apollogeddon/forgepy/commit/42bcb3248808883457badbfc69b3729142e7745d))
* enable --strict-markers and --strict-config for pytest ([e1d6cd5](https://github.com/Apollogeddon/forgepy/commit/e1d6cd532db7136802f1b790b1eae125173a4e47))
* expand shipped ruff rules with security/naming/pathlib/perf checks ([1150257](https://github.com/Apollogeddon/forgepy/commit/11502571bf3f594b51ed1a4900b1ba1f55e6527f))
* runs_on input on every reusable workflow, passed down to each job ([d6ab993](https://github.com/Apollogeddon/forgepy/commit/d6ab993d90537f86c44a3040291f483f9022f58a))
* surface .forgepy config drift via pre-commit hook and CI check ([4a0aef9](https://github.com/Apollogeddon/forgepy/commit/4a0aef97c4b4c7d78e318c4f41660b32b9410fdc))
* test_on_push and test_release_prs, so a change is checked once, on its pr ([7e185be](https://github.com/Apollogeddon/forgepy/commit/7e185bebee8250c743a81a22aff87639b4f44c52))
* wire full feature pipeline together ([4b7882e](https://github.com/Apollogeddon/forgepy/commit/4b7882e5cdf85cc87eb2a4510e60b5e20ba66e8a))


### Bug Fixes

* add missing watchdog and validate-pyproject toolchain deps ([5ff11e4](https://github.com/Apollogeddon/forgepy/commit/5ff11e40a37a4f4326c3790d53fe2ad8333942dc))
* add pre-push basedpyright hook to match declared install-hook-types ([45c90f4](https://github.com/Apollogeddon/forgepy/commit/45c90f4c5c700ab39cfe58bc286fbb8ca4a35180))
* add release-please config under .github and scaffold it ([4191df2](https://github.com/Apollogeddon/forgepy/commit/4191df2ff65235291639a38b38ecc9c2a64aa0cd))
* add set_shell_task and set_key_if_absent pyproject helpers ([c44aa3e](https://github.com/Apollogeddon/forgepy/commit/c44aa3e3e581303b388980d593f1e1fdb6f877f1))
* always add the forgepy toolchain from git and skip build-system for websites ([e1c1174](https://github.com/Apollogeddon/forgepy/commit/e1c11747205e872728c1e586565bb54b559b40d0))
* auto-merge dependabot PRs of all update types, not just minor/patch ([418cf72](https://github.com/Apollogeddon/forgepy/commit/418cf72f4828d557a9a5ca983523cefb435d8dda))
* **ci:** add run_tests and enable_versioning inputs and fix drift check and deb job ([5436a72](https://github.com/Apollogeddon/forgepy/commit/5436a727d934d5266584a39c22630b399c39bdca))
* **ci:** gate auto-merge on testing in service, debian and website workflows ([2f10264](https://github.com/Apollogeddon/forgepy/commit/2f102649f6b373aca3f2382afc200342157ac078))
* contain tomlkit's untyped API and resolve strict pyright errors ([499d6a0](https://github.com/Apollogeddon/forgepy/commit/499d6a07fec7b3b32f660cae3dfde03ec1c53539))
* create placeholder test file so pyrightconfig include path resolves ([9ebe005](https://github.com/Apollogeddon/forgepy/commit/9ebe0054d7596041ee4838ca79710c4daa4cd8cf))
* Debian packaging produced an unversioned, non-portable .deb ([11ba39d](https://github.com/Apollogeddon/forgepy/commit/11ba39daead7619ffc08fe51326f492eb4d540d9))
* **deps:** bump ruff from 0.16.9 to 0.16.10 in the dependencies group ([2d8c892](https://github.com/Apollogeddon/forgepy/commit/2d8c8924382c9ceb926536ff2b01ec9125be4395))
* **deps:** bump ruff from 0.16.9 to 0.16.10 in the dependencies group ([6af8185](https://github.com/Apollogeddon/forgepy/commit/6af81856348ce72e546787e75c2524ef41054a7a))
* **deps:** update uv-build requirement from &lt;0.9,&gt;=0.7 to &gt;=0.7,&lt;0.13 ([d2a7598](https://github.com/Apollogeddon/forgepy/commit/d2a7598c5444241b18628a96efc0fd2e6a75732f))
* **deps:** update uv-build requirement from &lt;0.9,&gt;=0.7 to &gt;=0.7,&lt;0.13 ([cf767af](https://github.com/Apollogeddon/forgepy/commit/cf767af655bfa72e6cef5d5eb370f257419dbae5))
* **docker:** run the backend image as non-root and make the uv version a build arg ([fe26af3](https://github.com/Apollogeddon/forgepy/commit/fe26af3b9d8bdfce5cbc885908d5722c831674f8))
* gate auto-merge on the testing job so it can't merge a failing PR ([0095055](https://github.com/Apollogeddon/forgepy/commit/00950552533bec0c8945638f79b85cfcb0ba76f1))
* honour --no-testing and --no-versioning in generated ci ([55c603c](https://github.com/Apollogeddon/forgepy/commit/55c603c124a0bcbae06fad8a268ef03c489d6e0b))
* keep docker.yml's merge job on github-hosted runners, as it needs a docker daemon ([9ba469a](https://github.com/Apollogeddon/forgepy/commit/9ba469ab55c39488e4359ab6a16d9ee2fb89e441))
* move per-file-ignores to child ruff.toml (base config extend doesn't apply them) ([3a94256](https://github.com/Apollogeddon/forgepy/commit/3a94256402764c3faaa6ff618bdad5147a27ab2f))
* pyrightconfig.json include crashed website mode and --no-testing ([04cab4a](https://github.com/Apollogeddon/forgepy/commit/04cab4a9f6abfefe4f93420e9521f946da122b71))
* scaffold starter package and disable uv packaging for website mode ([7548d19](https://github.com/Apollogeddon/forgepy/commit/7548d19a109504d031ae43bdf15271043ed1234f))
* use shell task type so lint and build-deb && chains actually run ([14186ad](https://github.com/Apollogeddon/forgepy/commit/14186ade12a9fdbd85fdea372f8f9edef79c3811))
* validate config in init so direct callers are protected ([3cc84fc](https://github.com/Apollogeddon/forgepy/commit/3cc84fc863394e3ebbe9ba24e2f3676f550d5917))


### Documentation

* add orange forgepy logo and unify README with forgejs ([4423b71](https://github.com/Apollogeddon/forgepy/commit/4423b7198e1af817bab0d121bbe049fa7d4bbf73))
* install from git and document pipeline inputs and docker changes ([64a06cb](https://github.com/Apollogeddon/forgepy/commit/64a06cbd3a6e96332cb0f2cc1d89c46bb2eb1891))
* note that nfpm is an external binary not installed via uv ([d86dba5](https://github.com/Apollogeddon/forgepy/commit/d86dba5f5e5bb7e4559c96a9a53d114f5118b3c5))
* write a real README with install, usage, and stack overview ([219cc2e](https://github.com/Apollogeddon/forgepy/commit/219cc2e1d9a6ccf5b16f93b30c5944eb3e59cf19))
