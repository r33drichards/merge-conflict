{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; with python3Packages; [
    python3
    numpy
    matplotlib
    scikit-learn
    ipykernel
    torch
    tqdm
    gymnasium
    torchvision
    tensorboard
    torch-tb-profiler
    opencv4
    tqdm
    # tensordict
  ];
  shellHook = ''
  export DYLD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [ pkgs.python3Packages.pytorch ]}
  python3 -m venv .venv
  # activate the virtual environment
  source .venv/bin/activate
  pip install 'gymnasium[atari]'
  pip install 'gymnasium[accept-rom-license]'
  pip install gym-super-mario-bros==7.4.0
  pip install torchrl==0.3.0
  pip install tensordict==0.3.0
  '';
}