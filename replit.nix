
{ pkgs }: {
  deps = [
    pkgs.python3Full
    pkgs.python3Packages.pip
    pkgs.python3Packages.setuptools
    pkgs.python3Packages.discordpy
    pkgs.python3Packages.aiohttp
    pkgs.python3Packages.python-dotenv
  ];
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      # Needed for pandas / numpy
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
      # Needed for pygame
      pkgs.glib
    ];
    PYTHONBIN = "${pkgs.python3Full}/bin/python3";
    LANG = "en_US.UTF-8";
  };
}
