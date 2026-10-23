"""Separate own-root receiver for missing Qwen capture inputs; never modifies phase3."""
import receive_stream
receive_stream.DIRS={'qwen25':'qwen25-3b-5defd279','qwen35':'qwen35-4b-851bf6e8'}
if __name__=='__main__':receive_stream.main()
