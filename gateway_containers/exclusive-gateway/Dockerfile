FROM continuumio/miniconda3 as base

ENV LIB_PATH /usr/src/app

RUN conda install anaconda-client

FROM base as reqs

WORKDIR ${LIB_PATH}
COPY environment.yml ${LIB_PATH}

RUN conda env update -f environment.yml

FROM reqs as container

COPY . .

RUN mkdir ${LIB_PATH}/tempFiles

ENV LISTEN_PORT 5000
ENV PATH /opt/conda/envs/tasks-api/bin:$PATH
RUN echo "source activate exclusive-gateway" > ~/.bashrc
EXPOSE ${LISTEN_PORT}

CMD ["/usr/src/app/entrypoint.sh"]