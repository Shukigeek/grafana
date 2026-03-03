from src.create_track import CreateTrack
import os



def main(json_path,url,drone_id):
    create_track = CreateTrack(path=json_path,url=url,id=drone_id)
    while True:
        create_track.publish_to_loki()

if __name__ == '__main__':
    drone_id = os.getenv("DRONE_ID", "0")
    main(json_path='coordinates.json',url='http://loki:3100/loki/api/v1/push',drone_id=drone_id)