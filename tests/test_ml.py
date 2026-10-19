from ml import predict


def test_predict_list_models():
    models = predict.list_models()
    assert isinstance(models, list)
    for m in models:
        assert "name" in m and "file" in m


def test_predict_discipline_shape():
    # Should return either error or structured dict
    res = predict.predict_discipline("Bachelor of Science in Computer Science")
    assert isinstance(res, dict)
    assert "error" in res or "predicted_discipline" in res


def test_recommend_similar_shape():
    res = predict.recommend_similar("software computing", 3)
    assert isinstance(res, dict)
    assert "error" in res or "items" in res
