FROM continuumio/miniconda3 as base
ENV LIB_PATH /usr/src/app
RUN conda install anaconda-client
WORKDIR ${LIB_PATH}
COPY environment.yml ${LIB_PATH}
RUN conda env update -f environment.yml
COPY . .
RUN mkdir ${LIB_PATH}/tempFiles
ENV LISTEN_PORT 5000
ENV FLASK_DEBUG 1
ENV PATH /opt/conda/envs/tasks-api/bin:$PATH
RUN echo "source activate parallel-gateway" > ~/.bashrc
EXPOSE ${LISTEN_PORT}

FROM base AS test

CMD ["echo", "TODO: run quick unit tests here."]

FROM base AS container

CMD ["/usr/src/app/entrypoint.sh"]