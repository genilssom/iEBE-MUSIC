FROM opensciencegrid/software-base:23-el9-release

MAINTAINER Chun Shen <chunshen@wayne.edu>

RUN yum -y install \
        cmake \
        cmake3 \
        git \
        eigen3-devel \
        gcc \
        gcc-c++ \
        gcc-gfortran \
        gsl-devel \
        fftw \
        fftw-devel \
        hdf5-devel \
        zlib-devel \
        make \
        openmpi-devel \
        python3 \
        python3-pip \
        time \
        vim \
        wget \
        openmpi \
        boost-devel \
        rsync \
        && \
    yum clean all

# Install pre-reqs python packages
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install \ 
    numpy==1.24.4 \
    scipy==1.10.1 \
     h5py \
     PyYAML \ 
     joblib \ 
     mpmath \ 
     freestream

ENV HOME /opt/

# download and compile the iEBE-MUSIC framework
RUN cd ${HOME} && \
    git clone https://github.com/genilssom/iEBE-MUSIC -b g_dev && \
    cd iEBE-MUSIC/codes && \
    bash get_code_packages.sh && \
    ./compile_code_packages.sh && \
    cd ../EOS_database && \
    bash download_EOSdatabase1D.sh && \
    bash download_QGPViscositydatabase1D.sh && \
    cd ../config/BESPost && \
    bash download_posteriorChain.sh && \
    cd ../arXiv_2408.00537 && \
    bash download_posteriorChain.sh

# Cleaning caches to reduce size of image
RUN yum clean all

ENV PYTHONIOENCODING utf-8
WORKDIR ${HOME}

RUN mkdir -p /opt/.local/share/trento
