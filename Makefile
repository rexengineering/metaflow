containers: flowd healthd throw catch

flowd: deploy/Dockerfile.flowd
	docker build -t $@ -f $< .

flowd.dev: deploy/Dockerfile.flowd.dev
	docker build -t flowd -f $< .

healthd: deploy/Dockerfile.healthd
	docker build -t $@ -f $< .

throw: deploy/Dockerfile.throw
	docker build -t $@-gateway:1.0.0 -f $< .

catch: deploy/Dockerfile.catch
	docker build -t $@-gateway:1.0.0 -f $< .

.PHONY: containers flowd flowd.dev healthd throw catch