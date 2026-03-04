# from src.create_track import CreateTrack
# from src.create_track_opensearch import CreateTrackOpensearch
import os
from src.simulate_flight import SimulatedFlight



def main(drone_id,json_path,pram_path):
    try:
    #     create_track = CreateTrack(path=json_path,url=loki_url,id=drone_id)
    #     create_track.publish_to_loki()
    # except Exception as e:
    #     print(e)
    # try:
    #     create_track_elastic = CreateTrackOpensearch(path=json_path,os_host=opensearch_url,drone_id=drone_id)
    #     create_track_elastic.publish_to_opensearch()
        simulate_flight = SimulatedFlight(drone_id=drone_id,cities_json_path=json_path,pram_json_path=pram_path)
        simulate_flight.run_simulation()
    except Exception as e:
        print(e)

if __name__ == '__main__':
    drone_id = os.getenv("DRONE_ID", "0")
    opensearch_url = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
    loki_url = os.getenv("LOKI_URL", "http://loki:3100/loki/api/v1/push")

    main(drone_id=drone_id,
         json_path='utils/coordinates.json',
         pram_path='utils/pram.json'
         )