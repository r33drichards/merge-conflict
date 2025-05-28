{
  description = "A basic rust cli";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  # inputs.unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";


  outputs = { self, nixpkgs, flake-utils, ... }@inputs:
    (flake-utils.lib.eachSystem [ "x86_64-linux" "x86_64-darwin" "aarch64-darwin" "aarch64-linux" ]
      (system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };

          devshell = pkgs.callPackage ./shell.nix { inherit pkgs;};

          # Create a script that runs the agent with a specific prompt file
          agentScript = promptFile: pkgs.writeScript "agent.sh" ''
            #!${pkgs.bash}/bin/bash
            ${pkgs.python3.withPackages (ps: with ps; [ anthropic tenacity ])}/bin/python3 ${./agent.py} --prompt-file ${promptFile}
          '';

          # Create the agent app with a specific prompt file
          agentApp = promptFile: flake-utils.lib.mkApp {
            drv = pkgs.writeScript "agent" (agentScript promptFile);
            exePath = "";
          };

        in
        {

          devShells.default = devshell;
          apps = {
            agent = agentApp ./prompt.md;  # Default agent using prompt.md
          };

        })
    );
}
