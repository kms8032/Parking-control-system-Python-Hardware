# Flask 서버 - 차량 번호 수신용
from flask import Flask, request, jsonify
from queue import Queue, Empty
from typing import Optional

app = Flask(__name__)

# 전역 큐 (main.py에서 주입)
car_number_queue: Optional[Queue] = None
response_queue: Optional[Queue] = None


def init_flask_server(input_queue: Queue, output_queue: Queue):
    """
    Flask 서버 초기화 - main.py에서 큐를 주입받음

    Args:
        input_queue: 차량 번호를 shortest_route로 전달하는 큐
        output_queue: shortest_route로부터 결과를 받는 큐
    """
    global car_number_queue, response_queue
    car_number_queue = input_queue
    response_queue = output_queue


@app.route('/entry', methods=['POST'])
def entry():
    """
    차량 번호를 수신하는 API

    Query Parameter:
        car_number: 차량 번호 (4자리)

    Example:
        POST /entry?car_number=1234

    Response:
        {
            "status": "success",
            "message": "차량 번호가 등록되었습니다.",
            "car_number": "1234",
            "parking_available": True
        }
    """
    try:
        # Query Parameter에서 차량 번호 가져오기
        car_number = request.args.get('car_number')

        # 차량 번호 유효성 검증
        if not car_number:
            return jsonify({
                "status": "error",
                "message": "car_number 쿼리 파라미터가 필요합니다.",
                "parking_available": False
            }), 400

        car_number = str(car_number).strip()

        if len(car_number) != 4:
            return jsonify({
                "status": "error",
                "message": "차량 번호는 4자리여야 합니다.",
                "car_number": car_number,
                "parking_available": False
            }), 400

        # 큐가 초기화되지 않은 경우
        if car_number_queue is None or response_queue is None:
            return jsonify({
                "status": "error",
                "message": "서버가 초기화되지 않았습니다.",
                "car_number": car_number,
                "parking_available": False
            }), 500

        # 큐에 차량 번호 저장
        car_number_queue.put(car_number)
        print(f"Flask 서버: 차량 번호 수신 및 Queue 저장 완료 - {car_number}")

        # shortest_route의 응답 대기 (최대 10초)
        try:
            response_data = response_queue.get(timeout=10)
            print(f"Flask 서버: shortest_route 응답 수신 - {response_data}")

            if response_data:
                return jsonify({
                    "status": "success",
                    "message": "차량 번호가 등록되었습니다.",
                    "car_number": car_number,
                    "parking_available": response_data
                }), 200

            else:
                return jsonify({
                    "status": "success",
                    "message": "주차 공간이 부족합니다.",
                    "car_number": car_number,
                    "parking_available": response_data
                }), 200

        except Empty:
            # 타임아웃 발생 시
            return jsonify({
                "status": "error",
                "message": "빈 주차 공간을 확인할 수 없습니다.",
                "car_number": car_number,
                "parking_available": False
            }), 500

    except Exception as e:
        print(f"Flask 서버 에러: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"서버 내부 오류: {str(e)}"
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        "status": "ok",
        "message": "Flask 서버가 정상 작동 중입니다."
    }), 200


def run_flask_server(car_number_data_queue: Queue, response_data_queue: Queue, port: int = 5005):
    """
    Flask 서버 실행 함수 (스레드에서 호출)

    Args:
        car_number_data_queue: 차량 번호를 shortest_route로 전달하는 Queue
        response_data_queue: shortest_route로부터 응답을 받는 Queue
        port: 서버 포트 번호 (기본값: 5005)
    """
    init_flask_server(car_number_data_queue, response_data_queue)
    print(f"Flask 서버 시작: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)


if __name__ == '__main__':
    # 테스트용 실행
    test_input_queue = Queue()
    test_output_queue = Queue()
    run_flask_server(test_input_queue, test_output_queue, port=5005)
