{
  description = "Reproducible experiment environment for Grid'5000 experiments";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

  outputs = { self, nixpkgs }:
  
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
  in {
    devShells.${system}.default = pkgs.mkShell {
      packages = with pkgs; [
        
        # Basic tools
        git
        vim
        tree
        
        # Java
        jdk17
	maven

        # Rust
        rustup
        rustc

        # Python
        python3
        uv
      ];

      shellHook = ''
            echo ""
            export PATH=$PATH:''${CARGO_HOME:-~/.cargo}/bin
            echo "  Grid'5000 dev shell"
            echo "  -------------------"
            echo "  java    : $(java -version 2>&1 | head -1)"
            echo "  rustc   : $(rustc --version)"
            echo "  python  : $(python3 --version)"
            echo "  uv      : $(uv --version)"
            echo ""
          '';
    };
  };
}
