{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; with python3Packages; [
    python
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
    nbconvert
    anthropic
    # tensordict
  ];
  shellHook = ''
  '';
}