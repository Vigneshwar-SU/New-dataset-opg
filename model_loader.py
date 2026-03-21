"""Model loader with compatibility fixes for older Keras models"""
import json
import h5py
import inspect
from tensorflow import keras
from tensorflow.keras import layers

class CompatibleSeparableConv2D(layers.SeparableConv2D):
    """Wrapper for SeparableConv2D that accepts and discards old model configs"""
    
    @classmethod
    def from_config(cls, config):
        if isinstance(config, dict):
            # Get the actual __init__ signature
            sig = inspect.signature(cls.__init__)
            valid_params = set(sig.parameters.keys())
            valid_params.add('self')
            
            # Filter config to only include valid parameters
            filtered_config = {}
            for key, value in config.items():
                if key in valid_params:
                    filtered_config[key] = value
            
            # Call parent with filtered config
            return layers.SeparableConv2D.from_config(filtered_config)
        return layers.SeparableConv2D.from_config(config)

def load_model(model_path):
    """Load model with compatibility fixes"""
    custom_objects = {'SeparableConv2D': CompatibleSeparableConv2D}
    try:
        return keras.models.load_model(model_path, custom_objects=custom_objects, compile=False)
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == '__main__':
    model = load_model('hypervision_OPG_model.h5')
    print("Model loaded successfully!")
    print(model.summary())
