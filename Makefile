SRC_CORE=client
CONTRACT_CORE=contracts
SRC_TEST=tests
SRC_RESOURCES=resources
DOTNET=dotnet
NEO3_BOA=neo3-boa
PYDOC=pydoc3
PIP=pip3
TESTENGINE=$(SRC_TEST)/TestEngine


# help:
# 	$(info Available commands:)
# 	$(info )
# 	@grep '^[[:alnum:]_-]*:.* ##' $(MAKEFILE_LIST) \
# 		| sort | awk 'BEGIN {FS=":.* ## "}; {printf "%-25s %s\n", $$1, $$2};'

help:
	@printf "%-20s %s\n" "Target" "Description"
	@printf "%-20s %s\n" "------" "-----------"
	@make -pqR : 2>/dev/null \
        | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' \
        | sort \
        | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' \
        | xargs -I _ sh -c 'printf "%-20s " _; make _ -nB | (grep -i "^# Help:" || echo "") | tail -1 | sed "s/^# Help: //g"'

.PHONY: help

run:
	@# Help: Run the client to mint an NFT
	@cd $(SRC_CORE); $(DOTNET) run -- -m 

build-contract: ## build the contract
	@# Help: Build the NFT contract with neo3-boa 
	@$(NEO3_BOA) $(CONTRACT_CORE)/ascii-nft.py

setup-testengine: | .$(TESTENGINE)
	@# Help: Clone and build the TestEngine to run the contract tests

.$(TESTENGINE):
	@echo "$(TESTENGINE) does not exist"
	@git clone https://github.com/simplitech/neo-devpack-dotnet.git -b v3.1.0 $(TESTENGINE) 
	@dotnet build $(TESTENGINE)/src/Neo.TestEngine/Neo.TestEngine.csproj

test-contract: 
	@# Help: Run the contract tests
	@cd tests/contract; python -m unittest discover

clean: ## Cleanup
	@# Help: Remove all client build artifacts
	@rm -rf $(SRC_CORE)/bin
	@rm -rf $(SRC_CORE)/obj

deps-install: ## Install the dependencies
	@# Help: Install the python dependencies (neo3-boa, pillow)
	@type $(PIP) >/dev/null 2>&1 || (echo "Run 'curl https://bootstrap.pypa.io/get-pip.py|sudo python3' first." >&2 ; exit 1)
	@$(PIP) install -r requirements.txt
