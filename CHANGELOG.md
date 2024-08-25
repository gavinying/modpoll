# Changelog

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
