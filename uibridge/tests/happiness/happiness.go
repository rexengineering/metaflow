package main

import (
	"log"
	"net/http"

	"github.com/gorilla/mux"
)

func RootHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(200)
	w.Write([]byte(`{"status": 0, "message": "Ok."}`))
	log.Println(r)
}

func main() {
	log.Println("Starting happiness server...")
	router := mux.NewRouter()
	router.HandleFunc("/", RootHandler).Methods("GET", "POST")
	http.ListenAndServe(":80", router)
}
