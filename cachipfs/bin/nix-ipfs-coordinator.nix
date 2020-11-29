let
  sources = import ../build/deps/sources.nix;
  nixpkgs = import sources.nixpkgs { };
in
  nixpkgs.stdenv.mkDerivation (
       (import ../build/deps/ctx.nix)
    // (rec {
      name = "nix-ipfs-node";

      buildInputs = [
        nixpkgs.cacert
        nixpkgs.python38
        nixpkgs.python38Packages.aioredis
        nixpkgs.python38Packages.starlette
        nixpkgs.python38Packages.uvicorn
        nixpkgs.python38Packages.uvloop
      ];

      repoSrcNixIpfsCoordinator = ../src/nix_ipfs_coordinator;
    })
  )
