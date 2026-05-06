#!/usr/bin/env bash

# download the code package

#download Isobar-Sampler
rm -fr isobar_sampler_code
git clone https://github.com/mluzum/Isobar-Sampler.git isobar_sampler_code
(cd isobar_sampler_code; git checkout bc586de03c26a3f3e4d6749e385ea015dcb204f2)
rm -fr isobar_sampler_code/.git

# download TRENTo
rm -fr trento_code
git clone https://github.com/jppicchetti/trento_sync.git trento_code
#(cd trento_code; git checkout ...)
#rm -fr trento_code/.gits

# download 3DMCGlauber
rm -fr 3dMCGlauber_code
git clone --depth=5 https://github.com/chunshen1987/3dMCGlauber 3dMCGlauber_code
#(cd 3dMCGlauber_code; git checkout 22955a36969429e99a85957eb6b3c231870a2015)
rm -fr 3dMCGlauber_code/.git

# download IPGlasma
rm -fr ipglasma_code
git clone --depth=1 https://github.com/chunshen1987/ipglasma -b ipglasma_jimwlk ipglasma_code
#(cd ipglasma_code; git checkout 4d4392724d05502c94bb8c512e382b6d9be9dec8)
rm -fr ipglasma_code/.git

# download KoMPoST
rm -fr kompost_code
git clone --depth=1 https://github.com/chunshen1987/KoMPoST kompost_code
#(cd kompost_code; git checkout ad5fe9d3b26434bb1d5c29820499ef26808b5a47)
rm -fr kompost_code/.git

# download MUSIC
rm -fr MUSIC_code
git clone --depth=3 https://github.com/luizafperin/MUSIC -b main music_code
#(cd MUSIC_code; git checkout e898cc826efc0303f2dd688602e6c604c9ef0f91)
rm -fr MUSIC_code/.git

# download iSS particle sampler
rm -fr iSS_code
git clone https://github.com/genilssom/iSS.git -b newRTA iss_code
#(cd iSS_code; git checkout b612a8e425d3e1dfc2d2b71cd208df6810c783be)
rm -fr iSS_code/.git

# download photonEmission wrapper
rm -fr photonEmission_hydroInterface_code
git clone --depth=1 https://github.com/chunshen1987/photonEmission_hydroInterface photonEmission_hydroInterface_code
#(cd photonEmission_hydroInterface_code; git checkout b80fb78c154cc9131162c8205615faffc86d6a49)
rm -fr photonEmission_hydroInterface_code/.git

# download UrQMD afterburner
rm -fr urqmd_code
git clone https://Chunshen1987@bitbucket.org/Chunshen1987/urqmd_afterburner.git urqmd_code
#(cd urqmd_code; git checkout 704c886)
rm -fr urqmd_code/.git

# download SMASH afterburner
rm -rf smash_code
git clone --depth=1 https://github.com/smash-transport/smash.git -b SMASH-3.2.2  smash_code
rm -rf smash_code/.git

# download and build Pythia8 (required to compile SMASH)
PYTHIA_VERSION="pythia8315"
PYTHIA_INSTALL_DIR="${HOME}/${PYTHIA_VERSION}"
if [ ! -f "${PYTHIA_INSTALL_DIR}/bin/pythia8-config" ]; then
    echo "Building Pythia8 in ${PYTHIA_INSTALL_DIR} ..."
    (
        cd /tmp
        wget --no-check-certificate \
            https://pythia.org/download/pythia83/${PYTHIA_VERSION}.tgz
        tar xzf ${PYTHIA_VERSION}.tgz
        cd ${PYTHIA_VERSION}
        ./configure --prefix=${PYTHIA_INSTALL_DIR}
        make -j2
        make install
        cd /tmp
        rm -rf ${PYTHIA_VERSION} ${PYTHIA_VERSION}.tgz
    )
else
    echo "Pythia8 already installed at ${PYTHIA_INSTALL_DIR}, skipping."
fi



# download hadronic afterner
rm -fr hadronic_afterburner_toolkit_code
git clone https://github.com/chunshen1987/hadronic_afterburner_toolkit -b main hadronic_afterburner_toolkit_code
#(cd hadronic_afterburner_toolkit_code; git checkout 1045565e1213bff1c28017c74d69a77ff8b5299e)
rm -fr hadronic_afterburner_toolkit_code/.git

#download deltaf_tables for iSS
(
  cd iSS_code/iSS_tables/deltaf_tables/urqmd
  bash download_NEoS4D_deltafCoeffs.sh
)

# download nucleus configurations for 3D-Glauber
(cd 3dMCGlauber_code/tables; bash download_nucleusTables.sh;)
# download nucleus configurations for IP-Glasma
(cd ipglasma_code/nucleusConfigurations; bash download_nucleusTables.sh;)
# download essential EOS files for hydro simulations
(cd music_code/EOS; bash download_hotQCD.sh; bash download_hotQCD.sh SMASH_binary; bash download_Neos2D.sh bqs; bash download_EOS-gp.sh)
