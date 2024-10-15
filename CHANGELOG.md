# Changelog

## [1.3.3](https://github.com/gavinying/modpoll/compare/v1.3.2...v1.3.3) (2024-10-15)


### Bug Fixes

* CI docs pipeline issue ([ada4089](https://github.com/gavinying/modpoll/commit/ada4089df1bb3063641820274a2c476d4a421321))

## [1.3.2](https://github.com/gavinying/modpoll/compare/v1.3.1...v1.3.2) (2024-10-15)


### Bug Fixes

* CI pipeline issue ([9386455](https://github.com/gavinying/modpoll/commit/9386455652025ea300dfdef5034738fa8936a66e))

## [1.3.1](https://github.com/gavinying/modpoll/compare/v1.3.0...v1.3.1) (2024-10-14)


### Bug Fixes

* Arguments mqtt-qos doesn't work for publish ([0a65d0a](https://github.com/gavinying/modpoll/commit/0a65d0ad1efe5067c080f7dd02afc1a8cb3c8478))
* Zsh parse error due to the special character used in mqtt-publish-topic-pattern. ([98230e8](https://github.com/gavinying/modpoll/commit/98230e8e78c77e7a0334d101ac990f53e599ce1d))

## [1.3.0](https://github.com/gavinying/modpoll/compare/v1.2.0...v1.3.0) (2024-10-13)


### Features

* Optimize code to make it more object oriented ([7195e29](https://github.com/gavinying/modpoll/commit/7195e297b5e658b05bb1c7c75c2d02f2ab886331))
* Remove importlib-metadata dependency since we drop support for pre-python3.8 environments. ([36a6fd4](https://github.com/gavinying/modpoll/commit/36a6fd43e81512af819cd7e00cdef4385e56e7ca))
* Support running multiple master instances ([#64](https://github.com/gavinying/modpoll/issues/64)) ([c44b597](https://github.com/gavinying/modpoll/commit/c44b597f45a1c9fd8b3b49562d74f959d21cd1f0))


### Bug Fixes

* Adjust delay to every loop iteration ([e368922](https://github.com/gavinying/modpoll/commit/e368922b925bcdf602d42716d2a72631f1134639))
* Allow github action to read the PR title and add labels ([22cb7c8](https://github.com/gavinying/modpoll/commit/22cb7c8dce284675193865c8fe399320bb0f2636))

## [1.2.0](https://github.com/gavinying/modpoll/compare/v1.1.0...v1.2.0) (2024-08-25)


### Features

* Introduce MQTT topic pattern to replace the existing MQTT topic prefix. ([58d3f67](https://github.com/gavinying/modpoll/commit/58d3f6719b7c78b0c17cfb60ca7013e5f8d1bccb))
* Add docker compose for better developer experience. ([01f15e8](https://github.com/gavinying/modpoll/commit/01f15e8d140eadf3413471463fbb26cd7d8fc175))


### Bug Fixes

* Validate action issue ([f8ef12e](https://github.com/gavinying/modpoll/commit/f8ef12e018009ec1c8b4d554829156e93c9a5b98))
* Typos ([9349864](https://github.com/gavinying/modpoll/commit/9349864c5712fad3da9218d8f8b72529da5e03fa))


## [1.1.0](https://github.com/gavinying/modpoll/compare/1.0.0...v1.1.0) (2024-08-03)


### Features

* add docker run commands for dev ([074d51e](https://github.com/gavinying/modpoll/commit/074d51e6196ca342d71c103e55a9c9e72cd3462b))
* add test cases for pytest ([99fc461](https://github.com/gavinying/modpoll/commit/99fc4613034e8aac1a24a760bfe395467a554092))
* support paho v2 ([#52](https://github.com/gavinying/modpoll/issues/52)) ([3e6681a](https://github.com/gavinying/modpoll/commit/3e6681a56497672c664a200e95728d7202a1964f))


### Bug Fixes

* allow user defined docker registry ([38acfcc](https://github.com/gavinying/modpoll/commit/38acfcc16f8143fe91e716ff734d4e96e8cc9035))
* device list is not properly used ([1824bed](https://github.com/gavinying/modpoll/commit/1824bede7a4085cf31243a261a7e074ad506c453))
* duplications in ci actions ([db5c667](https://github.com/gavinying/modpoll/commit/db5c667138afa4d0226b77655a4abe179bce866a))
* paho v2 changes in callbacks ([09316f8](https://github.com/gavinying/modpoll/commit/09316f8e8c247148d22f1b56a60fd35d6072ab6f))
* poetry warning ([44ec61f](https://github.com/gavinying/modpoll/commit/44ec61fd159e89b630ded9674c0a535cd1ba1a60))
* Unexpected input for release-please ([24703fe](https://github.com/gavinying/modpoll/commit/24703fe098379016447ab50ab89276e0f0f734ef))


### Documentation

* update CHANGELOG.md ([73fcc01](https://github.com/gavinying/modpoll/commit/73fcc010cb0ddbf4a1aa149ac28a354cd1bc5c39))


## [1.0.0](https://github.com/gavinying/modpoll/compare/0.8.4...1.0.0) (2024-07-11)


### ⚠ BREAKING CHANGES

* Release v1.0.0

### Features

* Support Modbus RTU/TCP/UDP devices

* Poll data from multiple Modbus devices

* Publish data to MQTT broker for remote debugging

* Log data for further investigation

* Provide docker solution for continuous data polling in production
